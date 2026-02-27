from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
#working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");
project_root = os.path.join(os.path.dirname(__file__), "..");

size = 300;
curves_info = [
    # Short Flory-Schulz, a=0.9
    (os.path.join(project_root,"stem-results"),
     r".*_dsu"+str(size)+r".*_a72.*.out", 
     "blue", 
     f"Flory-Schulz Distribution 2-30, $\chi = 0.72$"
     ),
    # Tophat from 20-30 DSU
    (os.path.join(project_root,"tophat-results"),
     r".*_dsu"+str(size)+r".*_a72.*.out", 
     "green", 
     f"Tophat Distribution 20-30, $\chi = 0.72$"),
    # Long Flory-Schulz, a=0.97
]
full_stress_figure(curves_info)
full_stress_ratio_figure(curves_info)
full_energy_ratio_figure(curves_info)
full_PE_figure(curves_info)