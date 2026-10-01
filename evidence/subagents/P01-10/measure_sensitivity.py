import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lammps_PG_objects import Atom, Bond
from process_pores import (
    analyze_periodic_network_image,
    chemical_connected_components,
)
from simulation_constants_settings import BOND_TYPE_GLYCAN


def atom(atom_id, molecule_id, x, y):
    return Atom(atom_id, molecule_id, 1, x, y, 0.0)


bounds = (0.0, 10.0, 0.0, 0.0, 10.0)
line_atoms = {1: atom(1, 1, 2.0, 5.0), 2: atom(2, 1, 8.0, 5.0)}
line_bonds = {1: Bond(1, BOND_TYPE_GLYCAN, 1, 2)}
settings = ((40, 40, 1), (80, 80, 1), (40, 40, 5))
measurements = []
for rows, columns, line_width in settings:
    metrics = analyze_periodic_network_image(
        line_atoms,
        line_bonds,
        bounds,
        image_shape=(rows, columns),
        line_width_pixels=line_width,
    )
    measurements.append(
        {
            "pixel_shape": list(metrics.pixel_shape),
            "line_width_pixels": metrics.line_width_pixels,
            "pixel_area": metrics.pixel_area,
            "occupied_fraction": metrics.occupied_fraction,
            "pore_pixel_counts": list(metrics.pore_pixel_counts),
            "pore_areas": list(metrics.pore_areas),
        }
    )

crossing_atoms = {
    1: atom(1, 1, 3.0, 5.0),
    2: atom(2, 1, 7.0, 5.0),
    3: atom(3, 2, 5.0, 3.0),
    4: atom(4, 2, 5.0, 7.0),
}
crossing_bonds = {
    1: Bond(1, BOND_TYPE_GLYCAN, 1, 2),
    2: Bond(2, BOND_TYPE_GLYCAN, 3, 4),
}
components = chemical_connected_components(crossing_atoms, crossing_bonds)

print(
    json.dumps(
        {
            "definition": "periodic complement of declared bond raster; not chemical pore ground truth",
            "line_fixture": measurements,
            "rendered_crossing_chemical_components": [
                sorted(component) for component in components
            ],
        },
        indent=2,
        sort_keys=True,
    )
)
