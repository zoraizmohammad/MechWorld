from process_pores import full_pore_size_distribution_figure
import os

project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results","090-FS")
filename_0 = "job12766370.1_dsu300_rho76_a75_prestr0.0";
filename_f = "job12766370.1_dsu300_rho76_a75_prestr0.13";

full_pore_size_distribution_figure(working_dir, filename_0, filename_f, use_cached_results=True, min_area_DSU2=1)