from process_network_ensembles import full_energy_ratio_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files
from simulation_constants_settings import DSU
import os
from sandbox_expected_tension import tension_xx, tension_yy

### START OF PROGRAM FOR TESTING
#
alpha_FS_str1 = "0.94"
alpha_FS_str2 = "0.93"
alpha_FS_str3 = "0.90"

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
dir_1 = os.path.join(project_root,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir_2 = os.path.join(project_root,"results",f"{alpha_FS_str2.replace(".","")}-FS");
dir_3 = os.path.join(project_root,"results",f"{alpha_FS_str3.replace(".","")}-FS");

def FS_label(alpha_str):
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

# These starting densities are chosen s.t. the network reaches 1 ATM of pressure at rho_f = 2.5 nm2 / DSU
# (see turgor pressure plot)
network_pattern_1 = regex_network_files(jobid=None, size=300, rho_0=0.60, isotropy=0.75)
network_pattern_2 = regex_network_files(jobid=None, size=300, rho_0=0.62, isotropy=0.75)
network_pattern_3 = regex_network_files(jobid=None, size=300, rho_0=0.72, isotropy=0.75)

curves_info = [
    (dir_1, network_pattern_1, "purple", FS_label(alpha_FS_str1), None),
    (dir_2, network_pattern_2, "blue",   FS_label(alpha_FS_str2), None),
    (dir_3, network_pattern_3, "green",  FS_label(alpha_FS_str3), None),
]

full_energy_ratio_figure(curves_information=curves_info, bsize=5E-3)

# Add vertical lines of 1 ATM pressure for each curve