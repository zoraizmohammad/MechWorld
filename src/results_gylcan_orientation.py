from process_orientation import full_orientation_delta_figure

working_dir = "C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\flory-schulz-092"
filename_without_ext = "job12531766.1_dsu300_rho70_a72"
#filename_without_ext = "job12402310.2_dsu300_rho100_a100"
#filename_without_ext = "job12402310.3_dsu300_rho100_a33"

full_orientation_delta_figure(working_dir, filename_without_ext)

# todo:
# Add axis labels 
# Add titles
# Fix/ignore orientation of periodic glycan strands