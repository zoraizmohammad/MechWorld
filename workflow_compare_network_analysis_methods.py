from ensemble_isotropic_strain import *
import shutil

def branch_networks_for_multiple_run_types(working_dirpath):
    filenames = os.listdir(working_dirpath)
    for filename in filenames:
        if re.match(r"^n\d+_.*\.network",filename):
            filepath = os.path.join(working_dirpath,filename)
            shutil.copy2(filepath,os.path.join(working_dirpath,"nve_"+filename))
            shutil.copy2(filepath,os.path.join(working_dirpath,"miniremap_"+filename))
            shutil.copy2(filepath,os.path.join(working_dirpath,"miniraw_"+filename))
            os.remove(filepath);

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"isostrain_compare_minimize_to_deform_012326");
isotropic_parameters = [0.33, 0.72, 1.0];
number_networks_per_group = 3;

# Subfunction to create folder if it not found
makedirs(working_dirpath, exist_ok=True)

# Loop to create networks
if len(os.listdir(working_dirpath)) == 0:
    create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 200, 1.0, isotropic_parameters, number_networks_per_group, False)
    branch_networks_for_multiple_run_types(working_dirpath)

# Run each network three times, using a different method
#run_networks_nve(working_dirpath, r"^nve_.*\.network$", rerun=False)                        # Wall Time = ?
#run_networks_minimize(working_dirpath, r"^miniremap_.*\.network$", rerun=False, remap=True) # Wall Time = 0:55:31 (30 steps), 0:59:29 (30 steps), 3:02:02 (300 DSU, 47 steps)
run_networks_minimize(working_dirpath, r"^miniraw_.*\_a72.network$", rerun=False, remap=False)  # Wall Time = ?

# Compare the results of each method
# Make functions to parse a just dirpath and a list of (regex, label, color, linestyle) for each of the plot types

curves_info = [
    (r"^nve_.*_a72\.out$", "red", "nve, $\chi = 0.72$"),
    (r"^miniraw_.*_a72\.out$", "blue", "miniraw, $\chi = 0.72$"),
    (r"^miniremap_.*_a72\.out$", "green", "miniremap, $\chi = 0.72$"),
]

full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info)