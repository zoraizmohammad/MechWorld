from process_network_ensembles import full_turgor_strain_figure
import os
from sandbox_expected_tension import tension_xx, tension_yy

### START OF PROGRAM FOR TESTING
#
alpha_FS_str = "0.93"


# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results",f"{alpha_FS_str.replace(".","")}-FS");

mean_final_density = 1 / (2.5/(1.03**2))
tol = 0.01;
rho_f_filter = (mean_final_density*(1-tol),mean_final_density*(1+tol))
print(rho_f_filter)

size = 300;
curves_info = [
    (working_dir, r".*_dsu"+str(size)+r".*_a75.*.out", "darkorange", r"$\rho_{f}$ = "+str(round(mean_final_density,3))+r", $\chi$ = 0.75, $\alpha_{FS}$ = "+alpha_FS_str),
]

full_turgor_strain_figure(curves_info,
                          density_filter=rho_f_filter)

print(rho_f_filter)