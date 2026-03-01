from assemble_pg_network import generate_pg_network, normalized_length_distribution, actual_length_distribution, process_distribution_string
import matplotlib.pyplot as plt
import matplotlib as mpl

size = 300;
rho = 0.7;
distribution = process_distribution_string("FS-2-100-0.95", size)
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, rho, 0.33, distribution, None, False);
print(f"density: ", density_fraction);
print(f"crosslink ratio: ", crosslink_ratio);

a, b = normalized_length_distribution(distribution);
c, d = actual_length_distribution(glycans, distribution);
plt.plot(a,b)
plt.plot(c,d)
plt.title("Target vs. Actual Glycan Length Distribution")
plt.xlabel("Glycan Length [DSU]")
plt.ylabel("Prevalence [a.u.]")
plt.show()