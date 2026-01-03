import numpy as np
import matplotlib.pyplot as plt
from assemble_pg_network import generate_pg_network

nPacking = 20;

tilt_factor_sweep = np.array([0.33, 0.72, 1.0])
packing_factor_sweep = np.linspace(0.1, 4, nPacking)
density_fraction_sweep = np.zeros([nPacking, len(tilt_factor_sweep)])
link_sweep             = np.zeros([nPacking, len(tilt_factor_sweep)])

#print(density_sweep)

for j, tilt_factor in enumerate(tilt_factor_sweep):
    for i, packing_factor in enumerate(packing_factor_sweep):
        print(tilt_factor, packing_factor)
        (density_fraction_sweep[i,j], link_sweep[i,j], _, _, _) = generate_pg_network(200, packing_factor, tilt_factor, None);

print(link_sweep)

plt.plot(density_fraction_sweep[:,0], link_sweep[:,0])
plt.plot(density_fraction_sweep[:,1], link_sweep[:,1])
plt.plot(density_fraction_sweep[:,2], link_sweep[:,2])
plt.title("Cross Linking vs. Density Parameter")
plt.legend([f"X = {tilt_factor_sweep[0]}",f"X = {tilt_factor_sweep[1]}",f"X = {tilt_factor_sweep[2]}"]);
plt.grid(True);
plt.xlabel("Density Fraction of Glycans");
plt.ylabel("Cross-linking Percentage");
plt.show();