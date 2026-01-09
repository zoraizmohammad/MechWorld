from assemble_pg_network import generate_pg_network

filename = "test1.data";
(density_fraction, crosslink_ratio, lst_atoms, lst_bonds, lst_angle) = generate_pg_network(200, 0.4, 0.72, filename)
print(f"New network written to: {filename}")
print(f"-> Cross-linking: {crosslink_ratio}")
print(f"-> Density Fraction (rho_mesh): {density_fraction}")