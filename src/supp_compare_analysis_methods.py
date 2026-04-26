from process_network_ensembles import *
import shutil

project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"stem-results");

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
#working_dirpath = os.path.join(os.path.curdir,"isostrain_compare_minimize_to_deform_012326");
working_dirpath = "C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\isostrain_compare_minimize_to_deform_012326"
isotropic_parameters = [0.33, 0.72, 1.0];
number_networks_per_group = 3;

curves_info = [
    (working_dir, r"^nve_.*_a72\.out$", "red", "nve, $\chi = 0.72$"),
    (working_dir, r"^miniraw_.*_a72\.out$", "blue", "miniraw, $\chi = 0.72$"),
    (working_dir, r"^miniremap_.*_a72\.out$", "green", "miniremap, $\chi = 0.72$"),
]

full_tension_figure(curves_info)
full_tension_ratio_figure(curves_info)
full_energy_ratio_figure(curves_info)
full_PE_figure(curves_info)