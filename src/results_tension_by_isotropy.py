from process_network_ensembles import *
from utils_helpers import PROJECT_ROOT_DIR, regex_network_files
from sandbox_expected_tension import tension_xx, tension_yy

### START OF PROGRAM FOR TESTING
# Settings
working_dir = os.path.join(PROJECT_ROOT_DIR,"results","090-FS");

re1 = regex_network_files(jobid=12837835, size=300, rho_0=0.76, isotropy=0.33)
re2 = regex_network_files(jobid=12837835, size=300, rho_0=0.76, isotropy=0.75)
re3 = regex_network_files(jobid=12837835, size=300, rho_0=0.76, isotropy=1.00)

curves_info = [
    (working_dir, re1, "darkorange", r", $\chi = 0.33$"),
    (working_dir, re2, "firebrick", r", $\chi = 0.75$"),
    (working_dir, re3, "navy", r", $\chi = 1.00$"),
]

full_tension_figure(curves_info)
full_tension_ratio_figure(curves_info, None, True)
#full_energy_ratio_figure(curves_info)
#full_PE_figure(curves_info)