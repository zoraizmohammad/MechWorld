from process_elastic_tensor import full_moduli_figure, full_poisson_ratios_figure
from utils_helpers import flory_schulz_mean_length
from simulation_constants_settings import DSU
import os

### START OF PROGRAM FOR TESTING
#
alpha_FS_str1 = "0.93"
alpha_FS_str2 = "0.90"

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
dir1 = os.path.join(project_root,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir2 = os.path.join(project_root,"results",f"{alpha_FS_str2.replace(".","")}-FS");

mean_final_density = 1 / (2.5/(DSU**2))
tol = 0.05;
rho_f_filter = None; #(mean_final_density*(1-tol),mean_final_density*(1+tol))

def FS_label(alpha_str):
    return r", $\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

size = 300;
curves_info = [
    (dir1, r"job12780.*_dsu"+str(size)+r".*_a75.*.moduli", "blue", FS_label(alpha_FS_str1)),
    (dir2, r"job12780.*_dsu"+str(size)+r".*_a75.*.moduli", "green", FS_label(alpha_FS_str2)),
]

full_moduli_figure(curves_info, rho_f_filter, thickness_nm=6.0)

full_poisson_ratios_figure(curves_info, rho_f_filter)

print(rho_f_filter)