from assemble_pg_network import generate_pg_network
from OLD import visualizeForceChains, assemble_boundary_sets
import matplotlib.pyplot as plt
import matplotlib as mpl

density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(100, 1.0, 0.33, None, True);
print(f"density: ", density_fraction);
print(f"crosslink ratio: ", crosslink_ratio);