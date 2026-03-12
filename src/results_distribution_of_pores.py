from process_pores import full_pore_size_distribution_figure
import os

project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results","flory-schulz-0925")
filename_0 = "job12603196.1_dsu300_rho70_a72_prestr0.0";
filename_f = "job12603196.1_dsu300_rho70_a72_prestr0.13";

full_pore_size_distribution_figure(working_dir, filename_0, filename_f, use_cached_results=True, min_area_DSU2=1)