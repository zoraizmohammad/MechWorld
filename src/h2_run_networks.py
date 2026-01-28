from ensemble_isotropic_strain import *

### START OF PROGRAM FOR TESTING
# Settings
# qrsh -l highp,h_data=4G,h_rt=24:00:00 -pe shared 8
# Should use our group node of n1847
working_dirpath = os.path.join(os.path.curdir,"isostrain_012726");
isotropic_parameters = [0.72];
number_networks_per_group = 3;

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