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
#create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 200, 1.0, isotropic_parameters, number_networks_per_group, False)
#branch_networks_for_multiple_run_types(working_dirpath)

run_networks_nve(working_dirpath, r"^nve_.*\.network$", False)
run_networks_minimize(working_dirpath, r"^miniremap_.*\.network$", False, True)
run_networks_minimize(working_dirpath, r"^miniraw_.*\.network$", False, False)