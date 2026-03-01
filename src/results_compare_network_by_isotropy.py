from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"stem-results");

size = 300;
curves_info = [
    (working_dir, r".*_dsu"+str(size)+r".*_a33.*.out", "red", f"{size} DSU, $\chi = 0.33$"),
    (working_dir, r".*_dsu"+str(size)+r".*_a72.*.out", "blue", f"{size} DSU, $\chi = 0.72$"),
    (working_dir, r".*_dsu"+str(size)+r".*_a100.*.out", "green", f"{size} DSU, $\chi = 1.00$"),
]
full_stress_figure(curves_info
                   (0.12, 0.14),
                   (0.0159586875, 0.031917375),
                   (0.031917375, 0.060794999999999995))
full_stress_ratio_figure(curves_info)
full_energy_ratio_figure(curves_info)
full_PE_figure(curves_info)