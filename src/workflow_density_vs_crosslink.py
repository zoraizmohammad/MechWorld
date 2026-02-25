from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from assemble_pg_network import generate_pg_network
from utils_helpers import get_confidence_intervals

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

def save_network_results_to_file(filename, size, rho_gap, tilt_factor):
    (rho_mesh, crosslinks, _, _, _, _) = generate_pg_network(size, rho_gap, tilt_factor, None);
    with open(filename, "a") as f:
        f.write(f"{size} {rho_gap} {tilt_factor} {rho_mesh} {crosslinks}\n")

def sweep_data_points(datafile : str, size : int):
    nPacking = 10;
    nSamples = 5;
    tilt_factor_sweep = np.array([0.33,0.72,1.00]);
    rho_gap_sweep = np.linspace(0.2, 2, nPacking);
    dNetworks = 1;
    tNetworks = len(tilt_factor_sweep)*len(rho_gap_sweep)*nSamples;

    for i, tilt_factor in enumerate(tilt_factor_sweep):
        for j, rho_gap in enumerate(rho_gap_sweep):
            for k in range(0,nSamples):
                print(f"Generating network {dNetworks}/{tNetworks}...")
                save_network_results_to_file(datafile, size, rho_gap, tilt_factor);
                dNetworks += 1;

def plot_crosslinks_vs_rho_gap(crosslinks_df, tilt : float, colorname : str, labelstr : str, linestylestr : str):
    filtered_crosslinks_df = crosslinks_df[crosslinks_df['tilt_factor'] == tilt]
    
    if len(filtered_crosslinks_df) == 0:
        raise ValueError(f"No networks were found with tilt_factor of {tilt}")
    
    ci_df = get_confidence_intervals(filtered_crosslinks_df, 0.95, 'rho_gap', 'crosslinks')

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

def finish_crosslinks_vs_rho_gap_fig():
    plt.xlabel(r'$\rho$_gap')
    plt.ylabel('$Crosslinking$')
    plt.title('crosslink_fraction vs rho_gap')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig('confidence_interval_plot.png')
    plt.show()

dsu_100_datafile = "results\\crosslinks100_stems.dump"
dsu_200_datafile = "results\\crosslinks200_stems.dump"
dsu_500_datafile = "results\\crosslinks500_stems.dump"
#sweep_data_points(dsu_100_datafile, 100)
#sweep_data_points(dsu_200_datafile, 200)
#sweep_data_points(dsu_500_datafile, 500)

crosslinks_100_df = import_crosslinks_data(dsu_100_datafile);
plot_crosslinks_vs_rho_gap(crosslinks_100_df, 0.33, "red", "X = 0.33, 100 DSU", ":")
plot_crosslinks_vs_rho_gap(crosslinks_100_df, 0.72, "blue", "X = 0.72, 100 DSU", ":")
plot_crosslinks_vs_rho_gap(crosslinks_100_df, 1.00, "black", "X = 1.00, 100 DSU", ":")
plot_expected_ranges([0.53361, 0.7086244], [0.4, 0.6])

#crosslinks_200_df = import_crosslinks_data(dsu_200_datafile);
#plot_crosslinks_vs_rho_gap(crosslinks_200_df, 0.33, "red", "X = 0.33, 200 DSU", "--")
#plot_crosslinks_vs_rho_gap(crosslinks_200_df, 0.72, "blue", "X = 0.72, 200 DSU", "--")
#plot_crosslinks_vs_rho_gap(crosslinks_200_df, 1.00, "black", "X = 1.00, 200 DSU", "--")

#crosslinks_500_df = import_crosslinks_data(dsu_500_datafile);
#plot_crosslinks_vs_rho_gap(crosslinks_500_df, 0.33, "red", "X = 0.33, 500 DSU", "-")
#plot_crosslinks_vs_rho_gap(crosslinks_500_df, 0.72, "blue", "X = 0.72, 500 DSU", "-")
#plot_crosslinks_vs_rho_gap(crosslinks_500_df, 1.00, "black", "X = 1.00, 500 DSU", "-")

finish_crosslinks_vs_rho_gap_fig()