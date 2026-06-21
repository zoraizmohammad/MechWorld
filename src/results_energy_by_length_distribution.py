from process_network_ensembles import full_energy_ratio_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files, PROJECT_ROOT_DIR
import os
import matplotlib.pyplot as plt

### START OF PROGRAM FOR TESTING
#
alpha_FS_str1 = "0.94"
alpha_FS_str2 = "0.93"
alpha_FS_str3 = "0.90"

# Settings
dir_1 = os.path.join(PROJECT_ROOT_DIR,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir_2 = os.path.join(PROJECT_ROOT_DIR,"results",f"{alpha_FS_str2.replace(".","")}-FS");
dir_3 = os.path.join(PROJECT_ROOT_DIR,"results",f"{alpha_FS_str3.replace(".","")}-FS");

def FS_label(alpha_str):
    return r" $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

# These starting densities are chosen s.t. the network reaches 1 ATM of pressure at rho_f = 2.5 nm2 / DSU
# (see turgor pressure plot)
network_pattern_1 = regex_network_files(jobid=12939337, size=300, rho_0=0.60, isotropy=0.75)
network_pattern_2 = regex_network_files(jobid=12939337, size=300, rho_0=0.62, isotropy=0.75)
network_pattern_3 = regex_network_files(jobid=12939337, size=300, rho_0=0.72, isotropy=0.75)

curves_info = [
    (dir_1, network_pattern_1, "purple", FS_label(alpha_FS_str1), None),
    (dir_2, network_pattern_2, "blue",   FS_label(alpha_FS_str2), None),
    (dir_3, network_pattern_3, "green",  FS_label(alpha_FS_str3), None),
]

ax = plt.subplot()

full_energy_ratio_figure(curves_information=curves_info, bsize=None, ax=ax)

# values taken from results_turgor.py with characteristic diameter of 1um
iso_p_1 = 0.202;
iso_p_2 = 0.231;
iso_p_3 = 0.320;

ax.plot([iso_p_1]*2, [0,0.9], linestyle="-.", color="purple")
ax.plot([iso_p_2]*2, [0,0.94], linestyle="-.", color="blue")
ax.plot([iso_p_3]*2, [0,0.9], linestyle="-.", color="green")

ofs = 0.02;
ax.text(iso_p_1-ofs, 0.91, "1 atm", color="purple")
ax.text(iso_p_2-ofs, 0.95, "1 atm", color="blue")
ax.text(iso_p_3-ofs, 0.91, "1 atm", color="green")

ax.set_ylim(0,1)

#plt.legend();
#plt.title("Fraction of Total Potential Energy")
plt.ylabel("Energy Fraction [a.u.]")
plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
plt.grid(True);
plt.show();
plt.show()

# Add vertical lines of 1 ATM pressure for each curve