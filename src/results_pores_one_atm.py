from process_pores import full_pore_sizes_regex_figure
from utils_helpers import PROJECT_ROOT_DIR, flory_schulz_mean_length
import os
import matplotlib.pyplot as plt

project_root = os.path.join(os.path.dirname(__file__), "..");
FS_090_DIR = os.path.join(PROJECT_ROOT_DIR,"results","090-FS")
FS_093_DIR = os.path.join(PROJECT_ROOT_DIR,"results","093-FS")
FS_094_DIR = os.path.join(PROJECT_ROOT_DIR,"results","094-FS")

def FS_label(alpha_str):
    #return r", $\alpha_{FS}$ = "+alpha_str+r", $\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"
    return r"$\bar{L}_{W} = "+str(round(flory_schulz_mean_length(alpha_str),1))+r"$ $DSU$"

curves_info = [
    (FS_090_DIR, r"job12939337.*_prestr0\.297\.atoms", FS_label(0.90), "green"),
    (FS_093_DIR, r"job12939337.*_prestr0\.211\.atoms", FS_label(0.93), "blue"),
    (FS_094_DIR, r"job12939337.*_prestr0\.182\.atoms", FS_label(0.94), "purple"),
]

ax = plt.subplot();

full_pore_sizes_regex_figure(curves_info, use_cached_results=True, min_area_sqDSU=1, ax=ax)

ax.set_title(r"Pore Areas; $\rho_f = 0.4$ $\frac{DSU}{nm^2}$, $P_t = 1 atm$")
ax.grid(True)
plt.show()