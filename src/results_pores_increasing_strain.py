from process_pores import full_pore_sizes_regex_figure
from utils_helpers import PROJECT_ROOT_DIR
import os
import matplotlib.pyplot as plt

project_root = os.path.join(os.path.dirname(__file__), "..");
FS_090_DIR = os.path.join(PROJECT_ROOT_DIR,"results","090-FS")
FS_093_DIR = os.path.join(PROJECT_ROOT_DIR,"results","093-FS")
FS_094_DIR = os.path.join(PROJECT_ROOT_DIR,"results","094-FS")

curves_info = [
    (FS_093_DIR, r"job12939337\.1_.*_prestr0\.4\.atoms", r"$\mathcal{E}=0.4$", "gray"),
    (FS_093_DIR, r"job12939337\.1_.*_prestr0\.3\.atoms", r"$\mathcal{E}=0.3$", "green"),
    (FS_093_DIR, r"job12939337\.1_.*_prestr0\.2\.atoms", r"$\mathcal{E}=0.2$", "blue"),
    (FS_093_DIR, r"job12939337\.1_.*_prestr0\.1\.atoms", r"$\mathcal{E}=0.1$", "red"),
]

ax = plt.subplot();

full_pore_sizes_regex_figure(curves_info, use_cached_results=True, min_area_sqDSU=1, ax=ax)

ax.legend(fontsize=15)
ax.set_title(r"Same Network, $\alpha=0.93$")
#ax.grid(True)
plt.show()