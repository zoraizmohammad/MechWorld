from assemble_pg_network import generate_pg_network

filename = "network_rho1_a100_w200.data";
(density_fraction, crosslink_ratio, lst_atoms, lst_bonds, lst_angle) = generate_pg_network(200, 1.0, 1.00, filename)
print(f"New network written to: {filename}")
print(f"-> Cross-linking: {density_fraction}")