"""P01-11 packaging and legacy-migration regression contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PROFILE_IDS = (
    "legacy_python_2026_03_12_v1",
    "legacy_direct_isotropic_pre_unit_fix_v1",
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1",
    "reviewed_physics_provisional_v0",
)
EXPECTED_PROFILE_HASHES = {
    "legacy_python_2026_03_12_v1": (
        "sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b"
    ),
    "legacy_direct_isotropic_pre_unit_fix_v1": (
        "sha256:9307aa15c01a557f671fff08d50793dccbf4837f0cd3c78eb0d3d9d7ab3b1df0"
    ),
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": (
        "sha256:b005c666d187538d60bbe6f924959473d6823e2287089e11621a1fc0dbc43771"
    ),
    "reviewed_physics_provisional_v0": (
        "sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5"
    ),
}
LEGACY_CORE_MODULES = {
    "assemble_pg_network",
    "import_data_from_dumps",
    "lammps_PG_objects",
    "process_elastic_tensor",
    "process_network_ensembles",
    "process_orientation",
    "process_pores",
    "run_lammps_elastic_tensor",
    "run_lammps_isotropic_strain",
    "simulation_constants_settings",
    "units",
    "utils_helpers",
}


def test_pyproject_declares_one_pgworld_doctor_console_surface() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]
    assert metadata["build-system"] == {
        "requires": ["setuptools==65.5.0", "wheel==0.45.1"],
        "build-backend": "setuptools.build_meta",
    }
    assert project["requires-python"] == ">=3.11"
    assert "authors" not in project
    assert project["scripts"] == {"pgworld": "pgworld.cli:main"}
    assert set(metadata["tool"]["setuptools"]["py-modules"]) == LEGACY_CORE_MODULES
    assert metadata["tool"]["setuptools"]["package-data"] == {
        "pgworld.config": ["profiles/*.json"]
    }


def _assert_git_content_identity(
    materialized_bytes: bytes, canonical_blob: bytes
) -> None:
    """Allow Git's LF-to-CRLF checkout conversion, but no content changes."""
    assert b"\r" not in canonical_blob
    normalized_materialized = materialized_bytes.replace(b"\r\n", b"\n")
    assert b"\r" not in normalized_materialized
    assert normalized_materialized == canonical_blob


def test_packaged_profiles_match_git_content_and_canonical_identity() -> None:
    packaged = SRC / "pgworld" / "config" / "profiles"
    assert {path.stem for path in packaged.glob("*.json")} == set(PROFILE_IDS)
    for profile_id in PROFILE_IDS:
        canonical_blob = subprocess.run(
            [
                "git",
                "show",
                f"HEAD:configs/physics/{profile_id}.json",
            ],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        packaged_bytes = (packaged / f"{profile_id}.json").read_bytes()
        _assert_git_content_identity(packaged_bytes, canonical_blob)
        snapshot = json.loads(packaged_bytes)
        assert snapshot["profile_id"] == profile_id
        assert snapshot["canonical_hash"] == EXPECTED_PROFILE_HASHES[profile_id]


def test_git_content_identity_allows_crlf_only_and_rejects_content_changes() -> None:
    canonical_blob = b'{\n  "profile_id": "fixture",\n  "value": 5570\n}\n'
    _assert_git_content_identity(canonical_blob, canonical_blob)
    _assert_git_content_identity(
        canonical_blob.replace(b"\n", b"\r\n"), canonical_blob
    )

    for index, original_byte in enumerate(canonical_blob):
        if original_byte == ord("\n"):
            continue
        replacement_byte = b"!" if original_byte != ord("!") else b"?"
        changed_content = (
            canonical_blob[:index] + replacement_byte + canonical_blob[index + 1 :]
        )
        with pytest.raises(AssertionError):
            _assert_git_content_identity(changed_content, canonical_blob)

    with pytest.raises(AssertionError):
        _assert_git_content_identity(canonical_blob.replace(b"\n", b"\r"), canonical_blob)


def _source_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(SRC), environment.get("PYTHONPATH", "")) if value
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def test_module_cli_exposes_only_doctor_and_preserves_machine_readable_output() -> None:
    help_result = subprocess.run(
        [sys.executable, "-B", "-m", "pgworld.cli", "--help"],
        cwd=ROOT,
        env=_source_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert help_result.returncode == 0
    assert "doctor" in help_result.stdout

    completed = subprocess.run(
        [sys.executable, "-B", "-m", "pgworld.cli", "doctor"],
        cwd=ROOT,
        env=_source_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    assert report["lammps"]["version_integer"] == 20260902
    assert report["lammps"]["closed"] is True
    assert report["bonded_fixture"]["physics_profile"] == {
        "profile_id": "legacy_python_2026_03_12_v1",
        "canonical_hash": (
            "sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b"
        ),
        "review_status": "legacy_unreviewed_reproduction_only",
        "units": report["bonded_fixture"]["physics_profile"]["units"],
        "biological_parameter_certification": False,
    }


def test_legacy_elastic_task_requires_explicit_forensic_and_delete_flags(
    tmp_path: Path,
) -> None:
    restart = tmp_path / "network_prestr0.0.restart"
    restart.write_bytes(b"not-a-real-restart")
    completed = subprocess.run(
        [sys.executable, "-B", str(SRC / "task_compute_elastic_tensor.py"), str(restart)],
        cwd=tmp_path,
        env=_source_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode != 0
    assert "--allow-legacy-forensic-output" in completed.stderr
    assert restart.exists()

    help_result = subprocess.run(
        [sys.executable, "-B", str(SRC / "task_compute_elastic_tensor.py"), "--help"],
        cwd=tmp_path,
        env=_source_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert help_result.returncode == 0
    assert "--allow-legacy-forensic-output" in help_result.stdout
    assert "--delete-restart" in help_result.stdout


def test_legacy_elastic_task_forensic_deletion_contract(
    monkeypatch, tmp_path: Path
) -> None:
    sys.path.insert(0, str(SRC))
    try:
        import task_compute_elastic_tensor as task

        calls: list[tuple[str, bool]] = []

        def succeed(path: str, *, allow_legacy_forensic_output: bool) -> bool:
            calls.append((path, allow_legacy_forensic_output))
            return True

        monkeypatch.setitem(
            sys.modules,
            "run_lammps_elastic_tensor",
            SimpleNamespace(lammps_calculate_elastic_tensor=succeed),
        )
        retained = tmp_path / "retained_prestr0.0.restart"
        retained.write_bytes(b"fixture")
        assert task.main([str(retained), "--allow-legacy-forensic-output"]) == 0
        assert retained.exists()
        assert calls[-1] == (str(retained.resolve()), True)

        deleted = tmp_path / "deleted_prestr0.0.restart"
        deleted.write_bytes(b"fixture")
        assert task.main(
            [
                str(deleted),
                "--allow-legacy-forensic-output",
                "--delete-restart",
            ]
        ) == 0
        assert not deleted.exists()

        def return_false(path: str, *, allow_legacy_forensic_output: bool) -> bool:
            return False

        monkeypatch.setitem(
            sys.modules,
            "run_lammps_elastic_tensor",
            SimpleNamespace(lammps_calculate_elastic_tensor=return_false),
        )
        rejected = tmp_path / "rejected_prestr0.0.restart"
        rejected.write_bytes(b"fixture")
        assert task.main(
            [
                str(rejected),
                "--allow-legacy-forensic-output",
                "--delete-restart",
            ]
        ) == 1
        assert rejected.exists()

        def fail(path: str, *, allow_legacy_forensic_output: bool) -> bool:
            raise RuntimeError("controlled solver failure")

        monkeypatch.setitem(
            sys.modules,
            "run_lammps_elastic_tensor",
            SimpleNamespace(lammps_calculate_elastic_tensor=fail),
        )
        failed = tmp_path / "failed_prestr0.0.restart"
        failed.write_bytes(b"fixture")
        try:
            task.main(
                [
                    str(failed),
                    "--allow-legacy-forensic-output",
                    "--delete-restart",
                ]
            )
        except RuntimeError as error:
            assert str(error) == "controlled solver failure"
        else:
            raise AssertionError("controlled solver failure did not propagate")
        assert failed.exists()
    finally:
        sys.path.remove(str(SRC))


def test_legacy_elastic_task_rejects_symlink_restart_before_deletion(
    monkeypatch, tmp_path: Path
) -> None:
    lexical_input = tmp_path / "link_prestr0.0.restart"
    lexical_input.write_bytes(b"fixture")
    monkeypatch.setattr(Path, "is_symlink", lambda _path: True)

    sys.path.insert(0, str(SRC))
    try:
        import task_compute_elastic_tensor as task

        monkeypatch.setitem(
            sys.modules,
            "run_lammps_elastic_tensor",
            SimpleNamespace(
                lammps_calculate_elastic_tensor=lambda *_args, **_kwargs: True
            ),
        )
        with pytest.raises(SystemExit) as denied:
            task.main(
                [
                    str(lexical_input),
                    "--allow-legacy-forensic-output",
                    "--delete-restart",
                ]
            )
        assert denied.value.code == 2
        assert lexical_input.exists()
    finally:
        sys.path.remove(str(SRC))
