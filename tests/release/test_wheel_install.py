"""Build and exercise the installable artifact outside the checkout."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile


ROOT = Path(__file__).resolve().parents[2]
LAMMPS_PYTHON = Path(
    r"C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python"
)
LEGACY_MODULES = (
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
)
PROFILE_IDS = (
    "legacy_python_2026_03_12_v1",
    "legacy_direct_isotropic_pre_unit_fix_v1",
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1",
    "reviewed_physics_provisional_v0",
)
PACKAGE_MODULES = {
    "pgworld/__init__.py",
    "pgworld/cli.py",
    "pgworld/doctor.py",
    "pgworld/config/__init__.py",
    "pgworld/config/physics_profiles.py",
    "pgworld/physics/__init__.py",
    "pgworld/physics/energy_force_virial.py",
    "pgworld/physics/lammps_oracle.py",
    "pgworld/simulation/__init__.py",
    "pgworld/simulation/controls.py",
    "pgworld/simulation/run_manager.py",
}


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None):
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    completed.elapsed_seconds = time.perf_counter() - started
    return completed


def test_wheel_installs_profiles_legacy_core_console_and_solver(tmp_path: Path) -> None:
    stage = tmp_path / "source"
    stage.mkdir()
    for filename in ("pyproject.toml", "README.md", "requirements.txt", "requirements.lock"):
        shutil.copy2(ROOT / filename, stage / filename)
    shutil.copytree(ROOT / "src", stage / "src")
    wheelhouse = tmp_path / "wheelhouse"
    build = _run(
        [
            sys.executable,
            "-B",
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(wheelhouse),
        ],
        cwd=stage,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = list(wheelhouse.glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    expected_payload = PACKAGE_MODULES | {
        f"{module}.py" for module in LEGACY_MODULES
    } | {
        f"pgworld/config/profiles/{profile_id}.json" for profile_id in PROFILE_IDS
    }
    dist_info_prefixes = {
        name.split("/", 1)[0]
        for name in names
        if name.split("/", 1)[0].endswith(".dist-info")
    }
    assert len(dist_info_prefixes) == 1
    dist_info_prefix = next(iter(dist_info_prefixes))
    allowed_dist_info = {
        f"{dist_info_prefix}/{filename}"
        for filename in (
            "METADATA",
            "WHEEL",
            "entry_points.txt",
            "top_level.txt",
            "RECORD",
        )
    }
    assert names == expected_payload | allowed_dist_info
    forbidden_parts = {
        "__pycache__",
        "artifacts",
        "checkpoints",
        "data",
        "dumps",
        "evidence",
        "images",
        "reports",
        "restarts",
        "results",
        "tests",
    }
    assert not any(forbidden_parts.intersection(Path(name).parts) for name in names)

    environment = tmp_path / "fresh-venv"
    created = _run(
        [sys.executable, "-B", "-m", "venv", str(environment)],
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stdout + created.stderr
    python = environment / "Scripts" / "python.exe"
    dependencies = _run(
        [
            str(python),
            "-B",
            "-m",
            "pip",
            "install",
            "-r",
            str(stage / "requirements.lock"),
        ],
        cwd=tmp_path,
    )
    assert dependencies.returncode == 0, dependencies.stdout + dependencies.stderr
    installed = _run(
        [str(python), "-B", "-m", "pip", "install", "--no-deps", str(wheel)],
        cwd=tmp_path,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    site_query = _run(
        [
            str(python),
            "-B",
            "-c",
            (
                "import pathlib,site; "
                "print(next(p for p in site.getsitepackages() "
                "if pathlib.Path(p).name == 'site-packages'))"
            ),
        ],
        cwd=tmp_path,
    )
    assert site_query.returncode == 0, site_query.stderr
    site_packages = Path(site_query.stdout.strip()).resolve()
    assert site_packages.is_relative_to(environment.resolve())
    (site_packages / "lammps-2Sep2026-external.pth").write_text(
        str(LAMMPS_PYTHON.resolve()) + "\n", encoding="utf-8"
    )

    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    doctor = _run(
        [str(environment / "Scripts" / "pgworld.exe"), "doctor"],
        cwd=tmp_path,
        env=clean_env,
    )
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    doctor_report = json.loads(doctor.stdout)
    assert doctor_report["lammps"]["version_integer"] == 20260902
    assert doctor_report["lammps"]["closed"] is True
    assert doctor_report["bonded_fixture"]["physics_profile"][
        "biological_parameter_certification"
    ] is False

    smoke_script = tmp_path / "installed_smoke.py"
    smoke_script.write_text(
        """
import importlib
import json
from pathlib import Path
import numpy as np
import sys

import pgworld
import lammps
from pgworld.config.physics_profiles import available_profile_ids, load_physics_profile
from pgworld.physics.energy_force_virial import PhysicsOracle
from pgworld.physics.lammps_oracle import run_lammps_bond_fixture
from pgworld.simulation.controls import CONTROL_SCHEMA_VERSION, build_deformation_schedule
import run_lammps_elastic_tensor as elastic

expected_hashes = {
    "legacy_python_2026_03_12_v1": "sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b",
    "legacy_direct_isotropic_pre_unit_fix_v1": "sha256:9307aa15c01a557f671fff08d50793dccbf4837f0cd3c78eb0d3d9d7ab3b1df0",
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": "sha256:b005c666d187538d60bbe6f924959473d6823e2287089e11621a1fc0dbc43771",
    "reviewed_physics_provisional_v0": "sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5",
}
profiles = {profile_id: load_physics_profile(profile_id) for profile_id in available_profile_ids()}
assert {key: value.canonical_hash for key, value in profiles.items()} == expected_hashes
profile = profiles["reviewed_physics_provisional_v0"]
positions = np.array([[0.0, 0.0], [1.2, 0.0]])
analytical = PhysicsOracle(profile).harmonic_bond(positions)
solver = run_lammps_bond_fixture(profile, style="harmonic", positions_nm=positions)
assert abs(analytical.energy_pN_nm - solver.energy_pN_nm) < 1.0e-12
np.testing.assert_allclose(analytical.forces_pN, solver.forces_pN, rtol=0.0, atol=1.0e-12)
np.testing.assert_allclose(
    analytical.virial_pN_nm,
    solver.configurational_virial_pN_nm,
    rtol=0.0,
    atol=1.0e-12,
)
assert solver.solver_version == 20260902 and solver.solver_closed is True

d = np.array([1.0, 0.875])
pair = np.vstack((-0.5 * d, 0.5 * d))
parameters = profile.expanded_snapshot()["potentials"]["harmonic_bond"]["parameters"]
radius = float(np.linalg.norm(d))
beta = 2.0 * parameters["K_pN_per_nm"] * (1.0 - parameters["r0_nm"] / radius)
tensor = (beta / 56.0) * np.outer(d, d)
base_total = 8.0 * np.array([tensor[0, 0], tensor[1, 1], tensor[0, 1]])
base = elastic.TangentBaseState.create(
    profile=profile,
    base_state_id="installed-tangent-base",
    cell_matrix_nm=np.array([[8.0, 0.0], [0.0, 7.0]]),
    base_total_tension_pN_per_nm=base_total,
    topology_id="installed-periodic-ring",
    branch_id="installed-smooth-branch",
    load_coordinate=0.0,
    minimization_converged=True,
    fixed_reference_id="installed-fixed-reference",
    fixed_reference_cell_matrix_nm=np.array([[8.0, 0.0], [0.0, 7.0]]),
    fixed_reference_total_tension_pN_per_nm=base_total,
    fixed_reference_topology_id="installed-periodic-ring",
    fixed_reference_branch_id="installed-smooth-branch",
    fixed_reference_load_coordinate=0.0,
    fixed_reference_minimization_converged=True,
)
tangent = elastic.run_lammps_harmonic_bond_tangent(
    profile,
    base_state=base,
    base_pair_positions_nm=pair,
    step_sizes=np.full(3, 1.0e-3),
)
assert tangent.solver_validation["solver_version"] == 20260902
assert tangent.solver_validation["instances_started"] == 7
assert tangent.solver_validation["instances_closed"] == 7
assert tangent.solver_validation["all_instances_closed"] is True

control_schedule = build_deformation_schedule({
    "schema_version": CONTROL_SCHEMA_VERSION,
    "config_id": "installed-axial-control-v1",
    "control_family": "deformation",
    "mode": "axial",
    "axes": {"x": "axial", "y": "hoop"},
    "fixed_reference_id": "installed-fixed-reference",
    "absolute_reference": "fixed_cell_equilibrated",
    "reference_reset_policy": "never",
    "load_coordinate_kind": "quasi_static_not_physical_time",
    "strain_unit": "dimensionless",
    "lambda_values": [0.0, 0.01],
})
assert control_schedule.steps[-1].absolute_deformation_gradient.tolist() == [
    [1.01, 0.0], [0.0, 1.0]
]
assert control_schedule.steps[-1].physical_time_valid is False

controls_module = importlib.import_module("pgworld.simulation.controls")
modules = {
    "pgworld": str(Path(pgworld.__file__).resolve()),
    "pgworld.simulation.controls": str(Path(controls_module.__file__).resolve()),
}
for name in %r:
    modules[name] = str(Path(importlib.import_module(name).__file__).resolve())
print(json.dumps({
    "modules": modules,
    "lammps_module": str(Path(lammps.__file__).resolve()),
    "sys_path": [str(Path(value).resolve()) for value in sys.path if value],
    "profile_hashes": expected_hashes,
    "p01_06": {
        "energy_error_pN_nm": abs(analytical.energy_pN_nm - solver.energy_pN_nm),
        "max_force_error_pN": float(np.max(np.abs(analytical.forces_pN - solver.forces_pN))),
        "max_virial_error_pN_nm": float(np.max(np.abs(analytical.virial_pN_nm - solver.configurational_virial_pN_nm))),
        "solver_closed": solver.solver_closed,
    },
    "p01_07": tangent.solver_validation,
    "p02_01": {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "mode": control_schedule.mode,
        "physical_time_claim": False,
    },
}, sort_keys=True))
""" % (LEGACY_MODULES,),
        encoding="utf-8",
    )
    smoke = _run([str(python), "-B", str(smoke_script)], cwd=tmp_path, env=clean_env)
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    evidence = json.loads(smoke.stdout)
    for module_path in evidence["modules"].values():
        resolved = Path(module_path).resolve()
        assert resolved.is_relative_to(site_packages)
        assert not resolved.is_relative_to(ROOT)
    assert Path(evidence["lammps_module"]).resolve().is_relative_to(
        LAMMPS_PYTHON.resolve()
    )
    checkout_roots = (ROOT.resolve(), (ROOT.parent / "MechWorld").resolve())
    for entry in evidence["sys_path"]:
        path = Path(entry).resolve()
        assert not any(path.is_relative_to(checkout) for checkout in checkout_roots)
    assert evidence["p01_06"]["solver_closed"] is True
    assert evidence["p01_06"]["max_force_error_pN"] < 1.0e-12
    assert evidence["p01_06"]["max_virial_error_pN_nm"] < 1.0e-12
    assert evidence["p01_07"]["instances_closed"] == 7

    check = _run(
        [str(python), "-B", "-m", "pip", "check"], cwd=tmp_path, env=clean_env
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert check.stdout.strip() == "No broken requirements found."
    locked = {}
    for line in (stage / "requirements.lock").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==", 1)
            locked[name.lower().replace("_", "-")] = version
    version_script = (
        "import importlib.metadata as m,json; "
        f"names={sorted(locked)!r}; "
        "print(json.dumps({n:m.version(n) for n in names},sort_keys=True))"
    )
    versions = _run([str(python), "-B", "-c", version_script], cwd=tmp_path, env=clean_env)
    assert versions.returncode == 0, versions.stderr
    assert json.loads(versions.stdout) == locked

    tamper_script = tmp_path / "tamper_profile.py"
    tamper_script.write_text(
        """
import json
from importlib import resources
from pgworld.config.physics_profiles import PhysicsProfileError, load_physics_profile

resource = resources.files("pgworld.config").joinpath(
    "profiles", "legacy_python_2026_03_12_v1.json"
)
payload = json.loads(resource.read_text(encoding="utf-8"))
payload["potentials"]["harmonic_bond"]["parameters"]["K_pN_per_nm"] = 1.0
resource.write_text(json.dumps(payload), encoding="utf-8")
try:
    load_physics_profile("legacy_python_2026_03_12_v1")
except PhysicsProfileError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise SystemExit("tampered installed profile was accepted")
""",
        encoding="utf-8",
    )
    tamper = _run([str(python), "-B", str(tamper_script)], cwd=tmp_path, env=clean_env)
    assert tamper.returncode == 0, tamper.stdout + tamper.stderr
    assert "PhysicsProfileError" in tamper.stdout

    evidence_path_text = os.environ.get("PGWORLD_WHEEL_EVIDENCE")
    if evidence_path_text:
        evidence_path = Path(evidence_path_text)
        report = {
            "schema_version": "pgworld.p01_11.wheel_verification.v1",
            "source_checkout": str(ROOT.resolve()),
            "temporary_root": str(tmp_path.resolve()),
            "fresh_environment": str(environment.resolve()),
            "fresh_site_packages": str(site_packages),
            "system_site_packages_enabled": False,
            "pythonpath_cleared": True,
            "external_lammps_python_path": str(LAMMPS_PYTHON.resolve()),
            "wheel": {
                "filename": wheel.name,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "members": sorted(names),
                "strict_allowlist_passed": names == expected_payload | allowed_dist_info,
            },
            "commands": {
                "build": build.args,
                "create_venv": created.args,
                "install_locked_dependencies": dependencies.args,
                "install_wheel": installed.args,
                "console_doctor": doctor.args,
                "installed_smoke": smoke.args,
                "pip_check": check.args,
                "locked_versions": versions.args,
                "tamper_check": tamper.args,
            },
            "results": {
                "build": {"exit_code": build.returncode, "elapsed_seconds": build.elapsed_seconds},
                "create_venv": {"exit_code": created.returncode, "elapsed_seconds": created.elapsed_seconds},
                "install_locked_dependencies": {
                    "exit_code": dependencies.returncode,
                    "elapsed_seconds": dependencies.elapsed_seconds,
                    "stdout": dependencies.stdout,
                    "stderr": dependencies.stderr,
                },
                "install_wheel": {"exit_code": installed.returncode, "elapsed_seconds": installed.elapsed_seconds},
                "console_doctor": {"exit_code": doctor.returncode, "elapsed_seconds": doctor.elapsed_seconds},
                "installed_smoke": {"exit_code": smoke.returncode, "elapsed_seconds": smoke.elapsed_seconds},
                "pip_check": {
                    "exit_code": check.returncode,
                    "elapsed_seconds": check.elapsed_seconds,
                    "stdout": check.stdout,
                },
                "locked_versions": json.loads(versions.stdout),
                "tamper_check": {
                    "exit_code": tamper.returncode,
                    "elapsed_seconds": tamper.elapsed_seconds,
                    "stdout": tamper.stdout,
                },
            },
            "doctor": doctor_report,
            "installed_smoke": evidence,
            "checkout_paths_absent_from_installed_sys_path": True,
            "private_or_generated_payload_absent": True,
            "limitations": [
                "LAMMPS 20260902 is supplied by an external installer path and has no Python distribution metadata.",
                "The exact requirements lock is verified for this CPython 3.11 Windows workstation, not as a universal binary lock.",
                "The fixtures validate numerical implementation consistency, not biological parameter correctness or public release readiness.",
            ],
        }
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
