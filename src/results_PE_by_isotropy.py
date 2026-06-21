from process_network_ensembles import full_energy_ratio_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files
import os

### START OF PROGRAM FOR TESTING
#
from process_network_ensembles import *
from utils_helpers import PROJECT_ROOT_DIR, regex_network_files
from sandbox_expected_tension import tension_xx, tension_yy


### START OF PROGRAM FOR TESTING
#
alpha_FS_str1 = "0.94"
alpha_FS_str2 = "0.93"
alpha_FS_str3 = "0.90"

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
dir1 = os.path.join(project_root,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir2 = os.path.join(project_root,"results",f"{alpha_FS_str2.replace(".","")}-FS");
dir3 = os.path.join(project_root,"results",f"{alpha_FS_str3.replace(".","")}-FS");

mean_final_density = 1 / (2.5/(DSU**2))
tol = 0.05;
rho_f_filter = None #(mean_final_density*(1-tol),mean_final_density*(1+tol))

def FS_label(alpha_str):
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

network_pattern = regex_network_files(jobid=12939337, size=300, rho_0=None, isotropy=0.75, extension = "out")

curves_info = [
    (dir1, network_pattern, "purple", FS_label(alpha_FS_str1)),
    (dir2, network_pattern, "blue",   FS_label(alpha_FS_str2)),
    (dir3, network_pattern, "green",  FS_label(alpha_FS_str3)),
]

full_PE_figure(curves_info)