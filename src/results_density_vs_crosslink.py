from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from assemble_pg_network import generate_pg_network, process_distribution_string
from utils_helpers import get_confidence_intervals, add_curve_with_ci, PROJECT_ROOT_DIR
import os.path

# https://rowannicholls.github.io/python/statistics/confidence_intervals.html

@dataclass
class CrosslinkStruct:
    size : int; 
    rho_gap : float;
    tilt_factor : float;
    rho_mesh : float;
    crosslinks : float;

def import_crosslinks_data(filename : str) -> pd.DataFrame:
    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    lst_structs : list[CrosslinkStruct] = list();
    for i in range(1,len(lines)):
        if lines[i].startswith("#"): # ignore
            continue;
        
        data = lines[i].split();

        struct = CrosslinkStruct(
            size        = int(data[0]),
            rho_gap     = float(data[1]),
            tilt_factor = float(data[2]),
            rho_mesh    = float(data[3]),
            crosslinks  = float(data[4]),
        );

        lst_structs.append(struct);

    df = pd.DataFrame([asdict(n) for n in lst_structs])
    return df;

def save_network_results_to_file(filename, size, rho_gap, tilt_factor, distribution):

    (rho_mesh, crosslinks, _, _, _, _) = generate_pg_network(size, float(rho_gap), float(tilt_factor), distribution);
    with open(filename, "a") as f:
        f.write(f"{size} {rho_gap} {tilt_factor} {rho_mesh} {crosslinks}\n")

def sweep_data_points(datafile : str, size : int):
    # Sweep options
    nPacking = 10;
    nSamples = 5;
    tilt_factor_sweep = np.array([0.33,0.72,1.00]);
    rho_gap_sweep = np.linspace(0.2, 2, nPacking);

    # make this now and reuse it across networks, it takes a second to build
    distribution = process_distribution_string("FS-2-100-0.925", size)

    # Output
    completed_networks = 1;
    total_num_networks = len(tilt_factor_sweep)*len(rho_gap_sweep)*nSamples;

    for i, tilt_factor in enumerate(tilt_factor_sweep):
        for j, rho_gap in enumerate(rho_gap_sweep):
            for k in range(0,nSamples):
                print(f"Generating network {completed_networks}/{total_num_networks}...")
                save_network_results_to_file(datafile, size, rho_gap, tilt_factor, distribution);
                completed_networks += 1;

def plot_crosslinks_vs_rho_gap(crosslinks_df, tilt : float, colorname : str, labelstr : str, linestylestr : str):
    filtered_crosslinks_df = crosslinks_df[crosslinks_df['tilt_factor'] == tilt]
    del crosslinks_df;
    
    if len(filtered_crosslinks_df) == 0:
        raise ValueError(f"No networks were found with tilt_factor of {tilt}")
    
    add_curve_with_ci(filtered_crosslinks_df, 'rho_gap', 'crosslinks', curve_linestyle=linestylestr, curve_color=colorname, curve_label_override=labelstr)

def plot_crosslinks_vs_rho_mesh(crosslinks_df, tilt : float, colorname : str, labelstr : str, linestylestr : str):
    filtered_crosslinks_df = crosslinks_df[crosslinks_df['tilt_factor'] == tilt]
    
    if len(filtered_crosslinks_df) == 0:
        raise ValueError(f"No networks were found with tilt_factor of {tilt}")
    
    ci_df = get_confidence_intervals(filtered_crosslinks_df, 0.95, 'rho_mesh', 'crosslinks')

    n = int(len(filtered_crosslinks_df) / len(ci_df));
    plt.plot(ci_df.index, ci_df['mean'], color=colorname, label=labelstr, linewidth=2, linestyle=linestylestr)
    plt.fill_between(
        ci_df.index, 
        ci_df['lower'], 
        ci_df['upper'], 
        color=colorname, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

def plot_expected_ranges(x,y):
    plt.fill_between([x[0],x[1]], [y[0],y[0]], [y[1],y[1]], alpha = 0.2, color="green")

def finish_crosslinks_vs_rho_gap_fig(ax : plt.Axes):
    plt.xlabel(r'$\rho$', fontsize=15)
    plt.ylabel(r'$\phi$', rotation=0, fontsize=15)
    #plt.title(r'$\phi$ vs $\rho$')
    ax.yaxis.set_label_coords(-0.1,0.5)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig(os.path.join(PROJECT_ROOT_DIR,'figures','Crosslinking.pdf'), format="PDF")
    plt.show()

dsu_200_datafile = os.path.join(PROJECT_ROOT_DIR,"results","crosslinks200_stems.dump")
dsu_300_datafile = os.path.join(PROJECT_ROOT_DIR,"results","crosslinks300_stems.dump")
dsu_500_datafile = os.path.join(PROJECT_ROOT_DIR,"results","crosslinks500_stems.dump")

if not os.path.exists(dsu_200_datafile):
    sweep_data_points(dsu_200_datafile, 200)

crosslinks_200_df = import_crosslinks_data(dsu_200_datafile);
ax = plt.axes();

plot_crosslinks_vs_rho_gap(crosslinks_200_df, 0.33, "red", r"$\chi = 0.33$", "-")
plot_crosslinks_vs_rho_gap(crosslinks_200_df, 0.72, "blue", r"$\chi = 0.72$", "-")
plot_crosslinks_vs_rho_gap(crosslinks_200_df, 1.00, "black", r"$\chi = 1.00$", "-")
plot_expected_ranges([0.53361, 0.7086244], [0.4, 0.6])

#selected_density = 0.67; #0.7;
#selected_density = 0.7;
#plt.plot([selected_density,selected_density],[0,0.9],"--")

finish_crosslinks_vs_rho_gap_fig(ax)