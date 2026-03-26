from process_network_ensembles import *
from sandbox_expected_tension import tension_xx, tension_yy

### START OF PROGRAM FOR TESTING
# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results","090-FS");

size = 300;
curves_info = [
    (working_dir, r".*_dsu"+str(size)+r"_rho76"+r".*_a33.*.out", "darkorange", f", $\chi = 0.33$"),
    (working_dir, r".*_dsu"+str(size)+r"_rho76"+r".*_a75.*.out", "firebrick", f", $\chi = 0.75$"),
    (working_dir, r".*_dsu"+str(size)+r"_rho76"+r".*_a100.*.out", "navy", f", $\chi = 1.00$"),
]
full_tension_figure(curves_info,
                    (0.23,0.27),
                    tension_xx,
                    tension_yy)
full_tension_ratio_figure(curves_info, None, True)
full_energy_ratio_figure(curves_info)
full_PE_figure(curves_info)