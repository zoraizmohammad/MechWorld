from process_network_ensembles import *
from utils_helpers import PROJECT_ROOT_DIR

### START OF PROGRAM FOR TESTING
# Settings
#working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");

rho0 = 0.62;
size = 300;
isotropy = 0.75;

size_re = r"dsu"+str(size)+r".*"
rho0_re = r"rho"+str(int(rho0*100)).replace(".",r"\.")+r".*"
isotropy_re = r"a"+str(int(isotropy*100))+r".*"
full_re = r".*" + size_re + rho0_re + isotropy_re + r"\.out"
print(full_re)

curves_info = [
    (os.path.join(PROJECT_ROOT_DIR,"results","090-FS"),
      full_re, 
      "orange", 
      f"Flory-Schulz Distribution 2-100, a=0.9, $\chi = 0.72$"
    ),
    (os.path.join(PROJECT_ROOT_DIR,"results","093-FS"),
      full_re, 
      "red", 
      f"Flory-Schulz Distribution 2-100, a=0.93, $\chi = 0.72$"
    ),
    (os.path.join(PROJECT_ROOT_DIR,"results","094-FS"),
      full_re, 
      "green", 
      f"Flory-Schulz Distribution 2-100, a=0.94, $\chi = 0.72$"
    )
]
full_tension_figure(
    curves_info,
    (0.23, 0.27),
    (0.0159586875, 0.031917375),
    (0.031917375, 0.060794999999999995));
full_tension_ratio_figure(curves_info)
full_energy_ratio_figure(curves_info)
full_PE_figure(curves_info)