from process_pores import full_pore_sizes_regex_figure
from utils_helpers import PROJECT_ROOT_DIR
import os

project_root = os.path.join(os.path.dirname(__file__), "..");
FS_093_DIR = os.path.join(PROJECT_ROOT_DIR,"results","093-FS")

curves_info = [
    (FS_093_DIR, r".*dsu300_rho62_a75_prestr0\.0", r"$\mathcal{E}=0.0$", "red"),
    (FS_093_DIR, r".*dsu300_rho62_a75_prestr0\.212", r"$\mathcal{E}=0.212$", "blue"),
    (FS_093_DIR, r".*dsu300_rho62_a75_prestr0\.212", r"$\mathcal{E}=0.212$", "green"),
]

full_pore_sizes_regex_figure(curves_info, use_cached_results=True, min_area_sqDSU=1)