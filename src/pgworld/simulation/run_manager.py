"""Collision-safe local run directories and solver lifecycle management.

This module is an adapter boundary around the inherited simulation functions.  It
does not change their mechanics or submit scheduler work.  Callers construct a
solver with the absolute paths in :class:`RunContext`, write all artifacts below
that run root, and migrate legacy entry points separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform as platform_module
import re
import subprocess
import sys
from threading import BoundedSemaphore
import time
from typing import Any, Callable, Mapping, Protocol, TypeVar


RUN_SCHEMA_VERSION = "pgworld.run.v1"
COMPUTE_SCHEMA_VERSION = "pgworld.compute.local.v1"
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class RunDirectoryExistsError(FileExistsError):
    """Raised when a run ID has already reserved its immutable directory."""


class UnsafeOutputPathError(ValueError):
    """Raised when an output path could alias or escape the requested root."""


class SolverHandle(Protocol):
    """Minimum lifecycle interface required from an injected solver."""

    def close(self) -> None:
        """Release native solver resources."""


@dataclass(frozen=True)
class LocalComputeConfig:
    """Resource policy for bounded local development runs.

    The semaphore limit is enforced by :class:`RunManager`.  Walltime and memory
    values are recorded policy limits; execution callbacks can cooperatively
    check the walltime with :meth:`RunContext.assert_within_deadline`.  This
    adapter intentionally has no scheduler-submission implementation.
    """

    max_concurrent_runs: int
    walltime_seconds: int
    threads_per_run: int
    memory_mb: int
    backend: str = "local"
    allow_scheduler_submission: bool = False
    allow_mpi: bool = False
    allow_gpu: bool = False
    schema_version: str = COMPUTE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != COMPUTE_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {COMPUTE_SCHEMA_VERSION!r}, "
                f"not {self.schema_version!r}"
            )
        if self.backend != "local":
            raise ValueError("backend must be 'local'; scheduler execution is unsupported")
        for field_name in (
            "max_concurrent_runs",
            "walltime_seconds",
            "threads_per_run",
            "memory_mb",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        for field_name in (
            "allow_scheduler_submission",
            "allow_mpi",
            "allow_gpu",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")
        if self.allow_scheduler_submission:
            raise ValueError("scheduler submission is disabled by the local run manager")
        if self.allow_mpi:
            raise ValueError("MPI execution is outside this local run manager")
        if self.allow_gpu:
            raise ValueError("GPU execution is outside this local smoke-run policy")

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_gpu": self.allow_gpu,
            "allow_mpi": self.allow_mpi,
            "allow_scheduler_submission": self.allow_scheduler_submission,
            "backend": self.backend,
            "max_concurrent_runs": self.max_concurrent_runs,
            "memory_mb": self.memory_mb,
            "schema_version": self.schema_version,
            "threads_per_run": self.threads_per_run,
            "walltime_seconds": self.walltime_seconds,
        }


def load_local_compute_config(path: Path | str) -> LocalComputeConfig:
    """Load and strictly validate a JSON local-compute policy."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("local compute config must be a JSON object")
    allowed = {
        "allow_gpu",
        "allow_mpi",
        "allow_scheduler_submission",
        "backend",
        "max_concurrent_runs",
        "memory_mb",
        "schema_version",
        "threads_per_run",
        "walltime_seconds",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unknown local compute config fields: {', '.join(unknown)}")
    return LocalComputeConfig(**payload)


@dataclass(frozen=True)
class SourceProvenance:
    """Code/runtime identity recorded with every run."""

    source_commit: str
    source_tree_hash: str
    source_dirty: bool
    python_implementation: str
    python_version: str
    platform: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "python_implementation": self.python_implementation,
            "python_version": self.python_version,
            "source_commit": self.source_commit,
            "source_dirty": self.source_dirty,
            "source_tree_hash": self.source_tree_hash,
        }

    @classmethod
    def from_git(cls, repository_root: Path | str) -> "SourceProvenance":
        """Collect deterministic commit/tree identity without changing Git state."""

        root = Path(repository_root).resolve()

        def git(*arguments: str) -> str:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip()
                raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
            return completed.stdout.strip()

        return cls(
            source_commit=git("rev-parse", "HEAD"),
            source_tree_hash=git("rev-parse", "HEAD^{tree}"),
            source_dirty=bool(git("status", "--porcelain", "--untracked-files=normal")),
            python_implementation=platform_module.python_implementation(),
            python_version=platform_module.python_version(),
            platform=platform_module.platform(),
        )


@dataclass(frozen=True)
class RunConfig:
    """Typed, portable inputs that define one immutable simulation run."""

    run_id: str
    output_root: Path
    seed: int
    parameters: Mapping[str, Any]
    schema_version: str = RUN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RUN_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {RUN_SCHEMA_VERSION!r}")
        if not isinstance(self.run_id, str) or not _RUN_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError(
                "run_id must start with an ASCII letter or digit and contain only "
                "letters, digits, '.', '_', or '-' (maximum 128 characters)"
            )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        object.__setattr__(self, "output_root", Path(self.output_root))
        if not isinstance(self.parameters, Mapping):
            raise ValueError("parameters must be a mapping")
        _canonical_json(dict(self.parameters))

    def expanded(self, compute: LocalComputeConfig) -> dict[str, Any]:
        """Return the portable configuration written into the run directory."""

        return {
            "artifact_layout": {
                "dumps": "dumps",
                "images": "images",
                "raw": "raw",
                "restarts": "restarts",
                "solver_log": "solver/log.lammps",
                "solver_screen": "solver/screen.txt",
            },
            "compute": compute.as_dict(),
            "parameters": dict(self.parameters),
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class RunPaths:
    """Absolute, run-scoped artifact locations supplied to the solver callback."""

    root: Path
    metadata: Path
    solver: Path
    restarts: Path
    dumps: Path
    images: Path
    raw: Path
    solver_log: Path
    solver_screen: Path
    expanded_config: Path
    provenance: Path
    status: Path


@dataclass(frozen=True)
class RunContext:
    """Run-scoped paths, solver arguments, and cooperative resource deadline."""

    run_id: str
    paths: RunPaths
    solver_arguments: tuple[str, ...]
    deadline_monotonic: float
    _monotonic: Callable[[], float]

    def assert_within_deadline(self) -> None:
        """Raise before new work when the configured local walltime has elapsed."""

        if self._monotonic() > self.deadline_monotonic:
            raise TimeoutError(f"run {self.run_id!r} exceeded its local walltime")


@dataclass(frozen=True)
class RunResult:
    """Successful run location and the accepted lifecycle record."""

    paths: RunPaths
    status: Mapping[str, Any]


_SolverT = TypeVar("_SolverT", bound=SolverHandle)


class RunManager:
    """Reserve immutable run roots and close solver handles on every exit path."""

    def __init__(
        self,
        compute: LocalComputeConfig,
        *,
        source_provenance: SourceProvenance | None = None,
        repository_root: Path | str | None = None,
        clock: Callable[[], str] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.compute = compute
        if source_provenance is None:
            if repository_root is None:
                repository_root = Path(__file__).resolve().parents[3]
            source_provenance = SourceProvenance.from_git(repository_root)
        self.source_provenance = source_provenance
        self._clock = clock or _utc_now
        self._monotonic = monotonic
        self._slots = BoundedSemaphore(compute.max_concurrent_runs)

    def run(
        self,
        config: RunConfig,
        *,
        solver_factory: Callable[[RunContext], _SolverT],
        execute: Callable[[_SolverT, RunContext], Any],
    ) -> RunResult:
        """Execute one run, retain diagnostics, and re-raise execution failures."""

        with self._slots:
            return self._run_in_slot(
                config,
                solver_factory=solver_factory,
                execute=execute,
            )

    def _run_in_slot(
        self,
        config: RunConfig,
        *,
        solver_factory: Callable[[RunContext], _SolverT],
        execute: Callable[[_SolverT, RunContext], Any],
    ) -> RunResult:
        paths = _reserve_run_paths(config)
        expanded = config.expanded(self.compute)
        expanded_text = _canonical_json(expanded)
        config_hash = hashlib.sha256(expanded_text.encode("utf-8")).hexdigest()
        provenance = {
            "config_hash": config_hash,
            "run_schema_version": config.schema_version,
            **self.source_provenance.as_dict(),
        }
        _write_new_text(paths.expanded_config, expanded_text)
        _write_new_text(paths.provenance, _canonical_json(provenance))

        started_at = self._clock()
        status: dict[str, Any] = {
            "config_hash": config_hash,
            "failure": None,
            "finished_at_utc": None,
            "quality_status": "incomplete",
            "result": None,
            "run_id": config.run_id,
            "schema_version": config.schema_version,
            "solver": {
                "close_attempted": False,
                "close_succeeded": None,
                "created": False,
            },
            "started_at_utc": started_at,
            "termination_reason": "started",
        }
        _write_new_text(paths.status, _canonical_json(status))

        context = RunContext(
            run_id=config.run_id,
            paths=paths,
            solver_arguments=(
                "-log",
                str(paths.solver_log),
                "-screen",
                str(paths.solver_screen),
            ),
            deadline_monotonic=(
                self._monotonic() + float(self.compute.walltime_seconds)
            ),
            _monotonic=self._monotonic,
        )

        phase = "solver_factory"
        solver: _SolverT | None = None
        result: Any = None
        primary_error: BaseException | None = None
        close_error: BaseException | None = None
        try:
            solver = solver_factory(context)
            if solver is None:
                raise TypeError("solver_factory returned None instead of a solver handle")
            status["solver"]["created"] = True
            phase = "execute"
            result = execute(solver, context)
            _canonical_json(result)
        except BaseException as error:
            primary_error = error
        finally:
            if solver is not None:
                status["solver"]["close_attempted"] = True
                try:
                    solver.close()
                except BaseException as error:
                    close_error = error
                    status["solver"]["close_succeeded"] = False
                else:
                    status["solver"]["close_succeeded"] = True

        if primary_error is not None:
            interrupted = not isinstance(primary_error, Exception)
            status["quality_status"] = "incomplete" if interrupted else "rejected"
            if interrupted:
                status["termination_reason"] = "interrupted"
            elif phase == "execute":
                status["termination_reason"] = "execution_error"
            else:
                status["termination_reason"] = f"{phase}_error"
            status["failure"] = _failure_record(primary_error, phase)
        elif close_error is not None:
            status["quality_status"] = "rejected"
            status["termination_reason"] = "close_error"
            status["failure"] = _failure_record(close_error, "close")
        else:
            status["quality_status"] = "accepted"
            status["termination_reason"] = "completed"
            status["result"] = result

        if primary_error is not None and close_error is not None:
            status["close_failure"] = _failure_record(close_error, "close")
        status["finished_at_utc"] = self._clock()
        _replace_text(paths.status, _canonical_json(status))

        if primary_error is not None:
            raise primary_error
        if close_error is not None:
            raise close_error
        return RunResult(paths=paths, status=status)


def _reserve_run_paths(config: RunConfig) -> RunPaths:
    output_root = config.output_root.expanduser()
    if output_root.exists() and output_root.is_symlink():
        raise UnsafeOutputPathError("output_root must not be a symbolic link")
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve()

    root = output_root / config.run_id
    if root.parent != output_root:
        raise UnsafeOutputPathError("run directory escaped output_root")
    try:
        root.mkdir(exist_ok=False)
    except FileExistsError as error:
        raise RunDirectoryExistsError(
            f"run directory already exists for run_id {config.run_id!r}: {root}"
        ) from error

    metadata = root / "metadata"
    solver = root / "solver"
    restarts = root / "restarts"
    dumps = root / "dumps"
    images = root / "images"
    raw = root / "raw"
    for directory in (metadata, solver, restarts, dumps, images, raw):
        directory.mkdir(exist_ok=False)
    return RunPaths(
        root=root,
        metadata=metadata,
        solver=solver,
        restarts=restarts,
        dumps=dumps,
        images=images,
        raw=raw,
        solver_log=solver / "log.lammps",
        solver_screen=solver / "screen.txt",
        expanded_config=metadata / "config.expanded.json",
        provenance=metadata / "provenance.json",
        status=metadata / "run_status.json",
    )


def _failure_record(error: BaseException, phase: str) -> dict[str, str]:
    return {
        "message": str(error),
        "phase": phase,
        "type": type(error).__name__,
    }


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _write_new_text(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _replace_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "LocalComputeConfig",
    "RunConfig",
    "RunContext",
    "RunDirectoryExistsError",
    "RunManager",
    "RunPaths",
    "RunResult",
    "SourceProvenance",
    "UnsafeOutputPathError",
    "load_local_compute_config",
]
