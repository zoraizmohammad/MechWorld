from process_network_ensembles import full_turgor_strain_figure
import os
from sandbox_expected_tension import tension_xx, tension_yy

### START OF PROGRAM FOR TESTING
#
alpha_FS_str1 = "0.93"
alpha_FS_str2 = "0.90"


# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
dir1 = os.path.join(project_root,"results",f"{alpha_FS_str1.replace(".","")}-FS");
dir2 = os.path.join(project_root,"results",f"{alpha_FS_str2.replace(".","")}-FS");

mean_final_density = 1 / (2.5/(1.03**2))
tol = 0.1;
rho_f_filter = (mean_final_density*(1-tol),mean_final_density*(1+tol))
print(rho_f_filter)

size = 300;
curves_info = [
    (dir1, r".*_dsu"+str(size)+r".*_a75.*.out", "darkorange", r"$\rho_{f}$ = "+str(round(mean_final_density,3))+r", $\alpha_{FS}$ = "+alpha_FS_str1),
    (dir2, r".*_dsu"+str(size)+r".*_a75.*.out", "darkorange", r"$\rho_{f}$ = "+str(round(mean_final_density,3))+r", $\alpha_{FS}$ = "+alpha_FS_str2),
]

full_turgor_strain_figure(curves_info,
                          density_filter=rho_f_filter)

print(rho_f_filter)