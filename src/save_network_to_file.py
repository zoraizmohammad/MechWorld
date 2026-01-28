from assemble_pg_network import generate_pg_network, normalized_length_distribution, actual_length_distribution
import matplotlib.pyplot as plt

filename = "test1.data";
(density_fraction, crosslink_ratio, glycans, atoms, bonds, angles) = generate_pg_network(200, 1.0, 1.00, filename)
print(f"New network written to: {filename}")
print(f"-> Cross-linking: {crosslink_ratio}")
print(f"-> Density Fraction (rho_mesh): {density_fraction}")

a, b = normalized_length_distribution();
c, d = actual_length_distribution();
plt.plot(a,b)
plt.plot(c,d)
plt.show()