from process_elastic_tensor import full_subplots_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files
from simulation_constants_settings import DSU
import os

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
    #return r", $\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

network_pattern = regex_network_files(jobid=None, size=300, rho_0=None, isotropy=0.75, extension = "moduli")

#shared_curve_filters = tuple([(mean_final_density*(1-tol),"rho_f",mean_final_density*(1+tol))])
shared_curve_filters = None

curves_info = [
    (dir1, network_pattern, "purple", FS_label(alpha_FS_str1),  shared_curve_filters),
    (dir2, network_pattern, "blue",   FS_label(alpha_FS_str2),  shared_curve_filters),
    (dir3, network_pattern, "green",  FS_label(alpha_FS_str3),  shared_curve_filters),
]

full_subplots_figure(curves_information = curves_info)