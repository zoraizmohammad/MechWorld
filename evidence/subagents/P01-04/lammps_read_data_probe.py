from pathlib import Path
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import assemble_pg_network as pg_network
from lammps import lammps


with tempfile.TemporaryDirectory(prefix="p01-04-") as temporary_directory:
    requested_path = Path(temporary_directory) / "fixture.network"
    distribution = pg_network.process_distribution_string("UNI=2=5", 12)
    written_path, metrics, export = pg_network.generate_pg_network(
        Ny=12,
        mesh_density=0.7,
        anisotropy=0.6,
        distribution=distribution,
        filepath=str(requested_path),
        seed=20261001,
        return_metrics=True,
    )

    solver = lammps(cmdargs=["-log", "none", "-screen", "none"])
    solver_version = solver.version()
    try:
        solver.command("units nano")
        solver.command("dimension 2")
        solver.command("boundary p p p")
        solver.command("atom_style molecular")
        solver.command("bond_style harmonic")
        solver.command("angle_style harmonic")
        solver.command(f"read_data {Path(written_path).as_posix()}")
        atom_count = solver.get_natoms()
    finally:
        solver.close()

    print(f"lammps_version={solver_version}")
    print(f"graph_sha256={metrics.graph_sha256}")
    print(f"written={Path(written_path).name}")
    print(f"atoms_expected={metrics.atom_count} atoms_loaded={atom_count}")
    print(f"coordinate_count={export.coordinate_count}")
    print(f"max_abs_coordinate_error={export.max_abs_coordinate_error:.17g}")
    print(f"rms_coordinate_error={export.rms_coordinate_error:.17g}")
    print("solver_closed=true")
