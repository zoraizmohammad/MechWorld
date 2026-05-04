from process_elastic_tensor import full_subplots_figure, full_positive_definite_figure
from utils_helpers import flory_schulz_mean_length, regex_network_files
from simulation_constants_settings import DSU
import os

### START OF PROGRAM FOR TESTING
#
alpha_FS = "0.93"

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results",f"{alpha_FS.replace(".","")}-FS");

def FS_label(alpha_str):
    #return r", $\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

re1 = regex_network_files(jobid=None, size=300, rho_0=0.6, isotropy=0.33, extension = "moduli")
re2 = regex_network_files(jobid=None, size=300, rho_0=0.6, isotropy=0.75, extension = "moduli")
re3 = regex_network_files(jobid=None, size=300, rho_0=0.6, isotropy=1.00, extension = "moduli")

shared_curve_filters = None

curves_info = [
    (working_dir, re1, "darkorange", r"$\chi = 0.33$", shared_curve_filters),
    (working_dir, re2, "firebrick",  r"$\chi = 0.75$", shared_curve_filters),
    (working_dir, re3, "navy",       r"$\chi = 1.00$", shared_curve_filters),
]

full_subplots_figure(curves_info)

full_positive_definite_figure(curves_info)