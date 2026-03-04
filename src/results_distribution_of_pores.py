from process_pores import full_pore_size_distribution_figure
import os

project_root = os.path.join(os.path.dirname(__file__), "..");
working_dir = os.path.join(project_root,"results","flory-schulz-093")
filename_0 = "job12531767.1_dsu300_rho70_a72.relaxed";
filename_f = "job12531767.1_dsu300_rho70_a72.final";

full_pore_size_distribution_figure(working_dir, filename_0, filename_f, use_cached_results=True, min_area_DSU2=1)