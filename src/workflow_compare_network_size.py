from ensemble_isotropic_strain import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"isostrain_compare_network_size_012526");
isotropic_parameters = [0.72];
number_networks_per_group = 10;

# Subfunction to create folder if it not found
makedirs(working_dirpath, exist_ok=True)

# Create networks
create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 100, 1.0, isotropic_parameters, number_networks_per_group, False)
create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 300, 1.0, isotropic_parameters, number_networks_per_group, False)
create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 400, 1.0, isotropic_parameters, number_networks_per_group, False)

# Run 'em
run_networks_minimize(working_dirpath, r"^.*_dsu100_.*\.network$", rerun=False, remap=True)
run_networks_minimize(working_dirpath, r"^.*_dsu300_.*\.network$", rerun=False, remap=True)
run_networks_minimize(working_dirpath, r"^.*_dsu400_.*\.network$", rerun=False, remap=True)

# Compare the results based on patch size
# Make functions to parse a just dirpath and a list of (regex, label, color, linestyle) for each of the plot types

curves_info = [
    (r".*_dsu100.*_a72\.out$", "red", "100 DSU, $\chi = 0.72$"),
    (r".*_dsu200.*_a72\.out$", "blue", "200 DSU, $\chi = 0.72$"),
    (r".*_dsu300.*_a72\.out$", "green", "300 DSU, $\chi = 0.72$"),
    (r".*_dsu400.*_a72\.out$", "orange", "400 DSU, $\chi = 0.72$"),
]

full_bonds_strain_figure(working_dirpath, r".*") # improve!

full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info) # units