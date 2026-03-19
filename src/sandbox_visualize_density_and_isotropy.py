from assemble_pg_network import generate_pg_network, normalized_length_distribution, actual_length_distribution, process_distribution_string
import matplotlib.pyplot as plt
from utils_helpers import PROJECT_ROOT_DIR
import os.path

size = 40;
rho = 0.7;
distribution = process_distribution_string("FS-2-30-0.9", size)

fig, ax = plt.subplots(3,2)
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 0.30, 0.6, distribution, plot_network_on_these_axes=ax[0,0]);
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 0.70, 0.6, distribution, plot_network_on_these_axes=ax[1,0]);
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 1.10, 0.6, distribution, plot_network_on_these_axes=ax[2,0]);
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 0.80, 0.33, distribution, plot_network_on_these_axes=ax[0,1]);
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 0.80, 0.72, distribution, plot_network_on_these_axes=ax[1,1]);
density_fraction, crosslink_ratio, glycans, atoms, bonds, angles = generate_pg_network(size, 0.80, 1.00, distribution, plot_network_on_these_axes=ax[2,1]);

ax[0,0].set_title(r"$\rho=0.3$")
ax[1,0].set_title(r"$\rho=0.7$")
ax[2,0].set_title(r"$\rho=1.1$")

ax[0,1].set_title(r"$\chi=0.33$")
ax[1,1].set_title(r"$\chi=0.72$")
ax[2,1].set_title(r"$\chi=1.0$")

fig.set_size_inches(6,10)
fig.savefig(os.path.join(PROJECT_ROOT_DIR,"figures","Impact_Of_Density_And_Isotropy.pdf"), format="PDF")

plt.show()