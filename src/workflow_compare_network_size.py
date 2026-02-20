from process_network_ensembles import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"results", "hoffman", "results");
working_dirpath = "C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\hoffman\\results"

# Compare the results based on patch size
# Make functions to parse a just dirpath and a list of (regex, label, color, linestyle) for each of the plot types

isotropy = 0.72;
regex_suffix = r"_a"+str(int(isotropy*100)) + r"\.out$"

#comparison_info = [
#    (r".*_dsu100.*" + regex_suffix, r".*_dsu400.*" + regex_suffix, "red", f"100 DSU vs 400 DSU"),
#    (r".*_dsu200.*" + regex_suffix, r".*_dsu400.*" + regex_suffix, "blue", f"200 DSU vs 400 DSU"),
#    (r".*_dsu300.*" + regex_suffix, r".*_dsu400.*" + regex_suffix, "green", f"300 DSU vs 400 DSU"),
#]
#plot_comparison_of_ensembles(working_dirpath, comparison_info)

curves_info = [
    (r".*_dsu100.*" + regex_suffix, "red", f"100 DSU, $\chi = {isotropy}$"),
    (r".*_dsu200.*" + regex_suffix, "blue", f"200 DSU, $\chi = {isotropy}$"),
    (r".*_dsu300.*" + regex_suffix, "green", f"300 DSU, $\chi = {isotropy}$"),
    (r".*_dsu400.*" + regex_suffix, "orange", f"400 DSU, $\chi = {isotropy}$"),
]
full_stress_figure(working_dirpath, curves_info)
full_stress_ratio_figure(working_dirpath, curves_info)
full_energy_ratio_figure(working_dirpath, curves_info)
full_PE_figure(working_dirpath, curves_info) # units