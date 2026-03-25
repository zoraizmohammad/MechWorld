from assemble_pg_network import generate_pg_network, normalized_length_distribution, actual_length_distribution, process_distribution_string
import matplotlib.pyplot as plt
import matplotlib as mpl

size = 30;
rho = 0.7;
isotropy = 0.5;
distribution = process_distribution_string("FS-2-15-0.9", size)
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, rho, isotropy, distribution, None, True);
#print(f"density: ", density_fraction);
#print(f"crosslink ratio: ", crosslink_ratio);

#a, b = normalized_length_distribution(distribution);
#c, d = actual_length_distribution(glycans, distribution);
#plt.plot(a,b)
#plt.plot(c,d)
#plt.title("Target vs. Actual Glycan Length Distribution")
#plt.xlabel("Glycan Length [DSU]")
#plt.ylabel("Prevalence [a.u.]")
#plt.show()

a,b = normalized_length_distribution(process_distribution_string("FS-2-100-0.90", 300), label=r"$\alpha=0.9")
plt.plot(a,b)
a,b = normalized_length_distribution(process_distribution_string("FS-2-100-0.93", 300), label=r"$\alpha=0.93")
plt.plot(a,b)
a,b = normalized_length_distribution(process_distribution_string("FS-2-100-0.96", 300), label=r"$\alpha=0.96")
plt.plot(a,b)
plt.show()