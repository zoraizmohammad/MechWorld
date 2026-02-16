from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");
working_dirpath = "C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\hoffman\\results"

# Compare the results based on patch size
# Make functions to parse a just dirpath and a list of (regex, label, color, linestyle) for each of the plot types

size = 300;

curves_info = [
    (r".*_dsu300.*_a33.*.out", "red", f"300 DSU, $\chi = 0.33$"),
    (r".*_dsu300.*_a72.*.out", "blue", f"300 DSU, $\chi = 0.72$"),
    (r".*_dsu300.*_a100.*.out", "green", f"300 DSU, $\chi = 1.00$"),
]
full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info) # units