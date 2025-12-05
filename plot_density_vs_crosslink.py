import numpy as np
import matplotlib.pyplot as plt
from assemble_pg_network import generate_pg_network

n = 5;
density_sweep = np.linspace(0.1, 5, n)
link_sweep = np.zeros(n)

#print(density_sweep)

for i, rho in enumerate(density_sweep):
    (link_sweep[i], _, _, _) = generate_pg_network(100, rho, 0.65, None);

plt.plot(density_sweep, link_sweep)
plt.title("Cross Linking vs. Density Parameter")
plt.xlabel("Density (rho)")
plt.ylabel("Cross-Linking Percentage (a.u.)")
plt.show()

# CHECK CURVE FIT FOR DIMENSIONAL ACCURACY
