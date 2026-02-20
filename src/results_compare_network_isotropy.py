from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");
working_dirpath = "C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\stem-results"

size = 300;
curves_info = [
    (r".*_dsu"+str(size)+r".*_a33.*.out", "red", f"{size} DSU, $\chi = 0.33$"),
    (r".*_dsu"+str(size)+r".*_a72.*.out", "blue", f"{size} DSU, $\chi = 0.72$"),
    (r".*_dsu"+str(size)+r".*_a100.*.out", "green", f"{size} DSU, $\chi = 1.00$"),
]
full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info) # units