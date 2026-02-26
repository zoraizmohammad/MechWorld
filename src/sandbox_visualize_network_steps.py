from assemble_pg_network import generate_pg_network, normalized_length_distribution, actual_length_distribution, create_FlorySchulz_distribution
import matplotlib.pyplot as plt
import matplotlib as mpl

distribution = create_FlorySchulz_distribution(5,100,0.97,1E7)
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(300, 1.0, 0.33, distribution, None, False);
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