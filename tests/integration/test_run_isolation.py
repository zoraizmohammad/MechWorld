"""Integration tests for isolated, provenance-recorded local solver runs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from threading import Barrier
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pgworld.simulation.run_manager import (  # noqa: E402
    LocalComputeConfig,
    RunConfig,
    RunDirectoryExistsError,
    RunManager,
    SourceProvenance,
    load_local_compute_config,
)


FIXED_PROVENANCE = SourceProvenance(
    source_commit="a" * 40,
    source_tree_hash="b" * 40,
    source_dirty=False,
    python_implementation="CPython",
    python_version="3.11.9",
    platform="test-platform",
)


class FakeSolver:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.closed = False

    def close(self) -> None:
        assert not self.closed
        self.closed = True


def _manager(*, max_concurrent_runs: int = 2) -> RunManager:
    return RunManager(
        LocalComputeConfig(
            max_concurrent_runs=max_concurrent_runs,
            walltime_seconds=30,
            threads_per_run=1,
            memory_mb=256,
        ),
        source_provenance=FIXED_PROVENANCE,
        clock=lambda: "2026-09-30T12:00:00Z",
    )


def _config(output_root: Path, run_id: str) -> RunConfig:
    return RunConfig(
        run_id=run_id,
        output_root=output_root,
        seed=17,
        parameters={"loading": {"max_strain": 0.01}, "mode": "smoke"},
    )


def test_local_compute_template_is_sanitized_and_disables_submission() -> None:
    template = ROOT / "configs" / "compute" / "local_smoke.json"
    scheduler_template = ROOT / "configs" / "compute" / "scheduler_disabled.json"

    config = load_local_compute_config(template)
    scheduler = json.loads(scheduler_template.read_text(encoding="utf-8"))
    serialized = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (template, scheduler_template)
    )

    assert config.backend == "local"
    assert config.max_concurrent_runs == 1
    assert config.allow_scheduler_submission is False
    assert config.allow_mpi is False
    assert config.allow_gpu is False
    assert scheduler["submission_enabled"] is False
    assert scheduler["account"] is None
    assert scheduler["working_directory"] is None
    assert scheduler["submit_command"] is None
    with pytest.raises(ValueError, match="unknown local compute config fields"):
        load_local_compute_config(scheduler_template)
    with pytest.raises(ValueError, match="scheduler submission is disabled"):
        LocalComputeConfig(
            max_concurrent_runs=1,
            walltime_seconds=30,
            threads_per_run=1,
            memory_mb=256,
            allow_scheduler_submission=True,
        )
    assert "@" not in serialized
    assert "/u/home/" not in serialized
    assert "c:\\users\\" not in serialized


def test_live_git_provenance_records_commit_tree_and_runtime() -> None:
    provenance = SourceProvenance.from_git(ROOT)

    assert len(provenance.source_commit) == 40
    assert len(provenance.source_tree_hash) == 40
    int(provenance.source_commit, 16)
    int(provenance.source_tree_hash, 16)
    assert isinstance(provenance.source_dirty, bool)
    assert provenance.python_implementation
    assert provenance.python_version
    assert provenance.platform


def test_success_records_deterministic_config_provenance_and_scoped_paths(
    tmp_path: Path,
) -> None:
    manager = _manager(max_concurrent_runs=1)
    solvers: list[FakeSolver] = []

    def solver_factory(context: Any) -> FakeSolver:
        solver = FakeSolver(context)
        solvers.append(solver)
        assert context.solver_arguments == (
            "-log",
            str(context.paths.solver_log),
            "-screen",
            str(context.paths.solver_screen),
        )
        return solver

    def execute(solver: FakeSolver, context: Any) -> dict[str, Any]:
        context.assert_within_deadline()
        context.paths.solver_log.write_text("local smoke\n", encoding="utf-8")
        (context.paths.restarts / "state.restart").write_text(
            "restart fixture\n", encoding="utf-8"
        )
        (context.paths.raw / "result.json").write_text("{}\n", encoding="utf-8")
        return {"states": 1}

    first = manager.run(
        _config(tmp_path / "first-root", "same-config"),
        solver_factory=solver_factory,
        execute=execute,
    )
    second = manager.run(
        _config(tmp_path / "second-root", "same-config"),
        solver_factory=solver_factory,
        execute=execute,
    )

    assert first.paths.root != second.paths.root
    assert first.paths.expanded_config.read_bytes() == second.paths.expanded_config.read_bytes()
    assert first.paths.provenance.read_bytes() == second.paths.provenance.read_bytes()
    assert all(solver.closed for solver in solvers)
    assert first.status["quality_status"] == "accepted"
    assert first.status["termination_reason"] == "completed"
    assert first.status["solver"] == {
        "created": True,
        "close_attempted": True,
        "close_succeeded": True,
    }
    assert first.status["failure"] is None
    assert first.status["result"] == {"states": 1}

    scoped_paths = (
        first.paths.solver_log,
        first.paths.solver_screen,
        first.paths.restarts,
        first.paths.dumps,
        first.paths.images,
        first.paths.raw,
    )
    assert all(path.is_relative_to(first.paths.root) for path in scoped_paths)
    assert not list(first.paths.root.rglob("*.tmp"))


def test_existing_run_is_refused_without_overwriting_accepted_raw_results(
    tmp_path: Path,
) -> None:
    manager = _manager(max_concurrent_runs=1)
    config = _config(tmp_path / "runs", "immutable-run")

    def write_accepted_result(_solver: FakeSolver, context: Any) -> dict[str, int]:
        context.paths.raw.joinpath("payload.txt").write_text(
            "accepted\n", encoding="utf-8"
        )
        return {"states": 1}

    first = manager.run(
        config,
        solver_factory=FakeSolver,
        execute=write_accepted_result,
    )
    payload = first.paths.raw / "payload.txt"

    with pytest.raises(RunDirectoryExistsError, match="immutable-run"):
        manager.run(
            config,
            solver_factory=FakeSolver,
            execute=lambda _solver, context: context.paths.raw.joinpath(
                "payload.txt"
            ).write_text("overwritten\n", encoding="utf-8"),
        )

    assert payload.read_text(encoding="utf-8") == "accepted\n"
    assert json.loads(first.paths.status.read_text(encoding="utf-8"))[
        "quality_status"
    ] == "accepted"


def test_invalid_run_identifiers_cannot_escape_or_alias_the_output_root(
    tmp_path: Path,
) -> None:
    for run_id in ("../escape", ".", "nested/run", "nested\\run", ""):
        with pytest.raises(ValueError, match="run_id"):
            _config(tmp_path / "runs", run_id)


@pytest.mark.parametrize(
    ("raised", "quality_status", "termination_reason"),
    [
        (RuntimeError("solver failed"), "rejected", "execution_error"),
        (KeyboardInterrupt(), "incomplete", "interrupted"),
    ],
)
def test_failure_and_interruption_close_solver_and_record_explicit_metadata(
    tmp_path: Path,
    raised: BaseException,
    quality_status: str,
    termination_reason: str,
) -> None:
    manager = _manager(max_concurrent_runs=1)
    solver_box: list[FakeSolver] = []
    config = _config(tmp_path / "runs", f"case-{termination_reason}")

    def solver_factory(context: Any) -> FakeSolver:
        solver = FakeSolver(context)
        solver_box.append(solver)
        return solver

    def execute(_solver: FakeSolver, context: Any) -> None:
        context.paths.raw.joinpath("partial.txt").write_text(
            "diagnostic retained\n", encoding="utf-8"
        )
        raise raised

    with pytest.raises(type(raised), match=str(raised) or None):
        manager.run(config, solver_factory=solver_factory, execute=execute)

    run_root = config.output_root / config.run_id
    status = json.loads((run_root / "metadata" / "run_status.json").read_text())
    assert solver_box[0].closed is True
    assert status["quality_status"] == quality_status
    assert status["termination_reason"] == termination_reason
    assert status["failure"] == {
        "message": str(raised),
        "phase": "execute",
        "type": type(raised).__name__,
    }
    assert status["solver"]["close_succeeded"] is True
    assert (run_root / "raw" / "partial.txt").read_text(encoding="utf-8") == (
        "diagnostic retained\n"
    )
    assert not list(run_root.rglob("*.tmp"))


def test_factory_failure_records_metadata_without_claiming_a_solver_close(
    tmp_path: Path,
) -> None:
    manager = _manager(max_concurrent_runs=1)
    config = _config(tmp_path / "runs", "factory-failure")

    def fail_factory(_context: Any) -> FakeSolver:
        raise RuntimeError("factory failed")

    with pytest.raises(RuntimeError, match="factory failed"):
        manager.run(config, solver_factory=fail_factory, execute=lambda *_args: None)

    status = json.loads(
        (config.output_root / config.run_id / "metadata" / "run_status.json").read_text()
    )
    assert status["quality_status"] == "rejected"
    assert status["termination_reason"] == "solver_factory_error"
    assert status["failure"]["phase"] == "solver_factory"
    assert status["solver"] == {
        "created": False,
        "close_attempted": False,
        "close_succeeded": None,
    }


def test_close_failure_rejects_run_and_records_close_metadata(tmp_path: Path) -> None:
    manager = _manager(max_concurrent_runs=1)
    config = _config(tmp_path / "runs", "close-failure")

    class CloseFailureSolver(FakeSolver):
        def close(self) -> None:
            raise RuntimeError("close failed")

    with pytest.raises(RuntimeError, match="close failed"):
        manager.run(
            config,
            solver_factory=CloseFailureSolver,
            execute=lambda _solver, _context: {"states": 1},
        )

    status = json.loads(
        (config.output_root / config.run_id / "metadata" / "run_status.json").read_text()
    )
    assert status["quality_status"] == "rejected"
    assert status["termination_reason"] == "close_error"
    assert status["failure"] == {
        "message": "close failed",
        "phase": "close",
        "type": "RuntimeError",
    }
    assert status["solver"] == {
        "created": True,
        "close_attempted": True,
        "close_succeeded": False,
    }


def test_bounded_concurrent_smokes_use_disjoint_artifact_trees(tmp_path: Path) -> None:
    manager = _manager(max_concurrent_runs=2)
    entered = Barrier(2)

    def execute(_solver: FakeSolver, context: Any) -> dict[str, str]:
        entered.wait(timeout=5)
        context.paths.solver_log.write_text(context.run_id, encoding="utf-8")
        context.paths.images.joinpath("frame.txt").write_text(
            context.run_id, encoding="utf-8"
        )
        context.paths.restarts.joinpath("state.restart").write_text(
            context.run_id, encoding="utf-8"
        )
        return {"run_id": context.run_id}

    configs = [_config(tmp_path / "runs", f"concurrent-{index}") for index in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                manager.run,
                config,
                solver_factory=FakeSolver,
                execute=execute,
            )
            for config in configs
        ]
        results = [future.result(timeout=10) for future in futures]

    assert len({result.paths.root for result in results}) == 2
    for result in results:
        run_id = result.status["run_id"]
        assert result.paths.solver_log.read_text(encoding="utf-8") == run_id
        assert result.paths.images.joinpath("frame.txt").read_text() == run_id
        assert result.paths.restarts.joinpath("state.restart").read_text() == run_id
        other = next(item for item in results if item is not result)
        assert not result.paths.root.is_relative_to(other.paths.root)
