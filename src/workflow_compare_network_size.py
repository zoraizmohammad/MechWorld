from ensemble_isotropic_strain import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"isostrain_compare_network_size_012526");
working_dirpath = "C:\\Users\\jrrm5\Desktop\\Eldredge\\PG-sims\\Github\\results\\hoffman\\results"

# Compare the results based on patch size
# Make functions to parse a just dirpath and a list of (regex, label, color, linestyle) for each of the plot types

curves_info = [
    (r".*_dsu100.*_a100\.out$", "red", "100 DSU, $\chi = 0.72$"),
    (r".*_dsu200.*_a100\.out$", "blue", "200 DSU, $\chi = 0.72$"),
    (r".*_dsu300.*_a100\.out$", "green", "300 DSU, $\chi = 0.72$"),
    (r".*_dsu400.*_a100\.out$", "orange", "400 DSU, $\chi = 0.72$"),
]

#full_bonds_strain_figure(working_dirpath, r".*") # improve!

full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info) # units