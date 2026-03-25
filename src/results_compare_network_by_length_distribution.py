from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
#working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");
project_root = os.path.join(os.path.dirname(__file__), "..");

size = 300;
curves_info = [
    (os.path.join(project_root,"results","090-FS"),
      r".*_dsu"+str(size)+r".*_a72.*.out", 
      "orange", 
      f"Flory-Schulz Distribution 2-100, a=0.9, $\chi = 0.72$"
    ),
    (os.path.join(project_root,"results","093-FS"),
      r".*_dsu"+str(size)+r".*_a72.*.out", 
      "red", 
      f"Flory-Schulz Distribution 2-100, a=0.93, $\chi = 0.72$"
    ),
    (os.path.join(project_root,"results","096-FS"),
      r".*_dsu"+str(size)+r".*_a72.*.out", 
      "green", 
      f"Flory-Schulz Distribution 2-100, a=0.96, $\chi = 0.72$"
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