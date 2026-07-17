from process_orientation import full_orientation_delta_figure
from utils_helpers import PROJECT_ROOT_DIR
import os

subplot_dir = os.path.join(PROJECT_ROOT_DIR, "results", "094-FS")

subplot_info = [
    (subplot_dir, "job13726230.30_dsu300_rho0.77_a75_link0.596_prestr0.0", r"$\epsilon_0 = 0.0$"),
    (subplot_dir, "job13726230.30_dsu300_rho0.77_a75_link0.596_prestr0.2", r"$\epsilon_0 = 0.2$"),
    (subplot_dir, "job13726230.30_dsu300_rho0.77_a75_link0.596_prestr0.4", r"$\epsilon_0 = 0.4$"),
]

full_orientation_delta_figure(curves=subplot_info)