from process_network_ensembles import full_turgor_strain_figure
from utils_helpers import flory_schulz_mean_length
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
dir1 = os.path.join(project_root,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir2 = os.path.join(project_root,"results",f"{alpha_FS_str2.replace(".","")}-FS");
dir3 = os.path.join(project_root,"results",f"{alpha_FS_str3.replace(".","")}-FS");

mean_final_density = 1 / (2.5/(DSU**2));
tol = 0.05;
rho_f_filter = (mean_final_density*(1-tol),mean_final_density*(1+tol));
print(rho_f_filter);

def FS_label(alpha_str):
    return r"$\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

size = 300;
curves_info = [
    (dir1, r".*_dsu"+str(size)+r".*_a75.*.out", "purple", FS_label(alpha_FS_str1)),
    (dir2, r"job12780.*_dsu"+str(size)+r".*_a75.*.out", "blue", FS_label(alpha_FS_str2)),
    (dir3, r".*_dsu"+str(size)+r".*_a75.*.out", "green", FS_label(alpha_FS_str3)),
]

full_turgor_strain_figure(curves_info,
                          density_filter=rho_f_filter)

print(rho_f_filter)