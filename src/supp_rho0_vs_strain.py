import matplotlib.pyplot as plt
import numpy as np

strain = np.linspace(0,0.4,100);
rho_f = 0.4;
rho_0 = rho_f * (1+strain)**2;

plt.plot(strain,rho_0,label=r"$\rho_f = 0.4$",color="black");
plt.legend()
plt.grid(True)
#plt.axis("Equal")
plt.ylabel(r"$\rho_0$", rotation=0, fontsize=15)
plt.ylim(0,0.85)
plt.xlabel(r"$\mathcal{E}$", fontsize=15)
plt.title(r"Relaxed Density ($\rho_0$) to obtain Post-Strain Density ($\rho_f$)")
plt.show()