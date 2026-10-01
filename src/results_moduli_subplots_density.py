from process_elastic_tensor import full_subplots_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files
from simulation_constants_settings import DSU
import os

### START OF PROGRAM FOR TESTING
#
alpha_FS_str = "0.93"

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
dir = os.path.join(project_root,"results",f"{alpha_FS_str.replace('.','')}-FS");

def FS_label(alpha_str):
    #return r", $\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

network_pattern_high_density = regex_network_files(jobid=None, size=300, rho_0=0.7, isotropy=0.75, extension = "moduli")
network_pattern_low_density = regex_network_files(jobid=None, size=300, rho_0=0.5, isotropy=0.75, extension = "moduli")

shared_curve_filters = None

curves_info = [
    (dir, network_pattern_high_density, "purple", "rho = 0.7",  shared_curve_filters),
    (dir, network_pattern_low_density, "blue", "rho = 0.5",  shared_curve_filters),
]

full_subplots_figure(curves_information = curves_info)
