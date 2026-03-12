from process_network_ensembles import *

# Settings
project_root = os.path.join(os.path.dirname(__file__), "..");

# 200,300,400
curves_info = [
    (os.path.join(project_root,"results","flory-schulz-0925-sizes"),
     r".*_dsu200"+r".*_a72.*.out", 
     "red", 
     f"Patch Size = 200 DSU, $\chi = 0.72$"
    ),
    (os.path.join(project_root,"results","flory-schulz-0925"),
     r".*_dsu300"+r".*_a72.*.out", 
     "blue", 
     f"Patch Size = 300 DSU, $\chi = 0.72$"
    ),
    (os.path.join(project_root,"results","flory-schulz-0925-sizes"),
     r".*_dsu400"+r".*_a72.*.out", 
     "green", 
     f"Patch Size = 400 DSU, $\chi = 0.72$"
    )
]

full_stress_figure(
    curves_info,
    (0.125, 0.135),
    (0.0159586875, 0.031917375),
    (0.031917375 , 0.060794999999999995));

full_stress_ratio_figure(curves_info)
full_energy_ratio_figure(curves_info)
#full_PE_figure(curves_info)