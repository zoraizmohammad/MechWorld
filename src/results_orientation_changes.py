from process_orientation import full_orientation_delta_figure
from utils_helpers import PROJECT_ROOT_DIR
import os

subplot_dir = os.path.join(PROJECT_ROOT_DIR, "results", "093-FS")

subplot_info = [
    (subplot_dir, "job12939337.19_dsu300_rho0.62_a75_link0.526_prestr0.1", r"$\epsilon_0 = 0.1$"),
    (subplot_dir, "job12939337.19_dsu300_rho0.62_a75_link0.526_prestr0.2", r"$\epsilon_0 = 0.2$"),
    (subplot_dir, "job12939337.19_dsu300_rho0.62_a75_link0.526_prestr0.3", r"$\epsilon_0 = 0.3$"),
    (subplot_dir, "job12939337.19_dsu300_rho0.62_a75_link0.526_prestr0.4", r"$\epsilon_0 = 0.4$"),
]

full_orientation_delta_figure(curves=subplot_info)