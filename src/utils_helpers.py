from scipy import stats
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import os

PROJECT_ROOT_DIR = os.path.join(os.path.dirname(__file__),"..")

def add_curve_with_ci(df, x_name, y_name, curve_linestyle = "-", curve_color = "black", curve_label_override = None):

    if curve_label_override == None:
        label_str = y_name;
    else:
        label_str = curve_label_override;

    ci_df = get_confidence_intervals(df, 0.95, x_name, y_name);
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=curve_color, linestyle=curve_linestyle, label=label_str)
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=curve_color, 
        alpha=0.2
    )

def find_files(dirpath, regex_pattern) -> set[str]:
    filepaths = set();
    for filename in os.listdir(dirpath):
        if re.search(regex_pattern, filename):
            new_filepath = os.path.join(dirpath,filename);
            filepaths.add(new_filepath);
    return filepaths;

def get_initial_density_from_filename(filename : str) -> float:
    rho_0_str = re.match(r".+_rho(\d+\.?\d+).+",filename).group(1);
    if ("." in rho_0_str):
        return float(rho_0_str)
    else:
        return float(rho_0_str)/100

def get_angle_between_vectors(v, u):
    return np.rad2deg(np.arccos(np.dot(v, u) / (np.linalg.norm(v)*np.linalg.norm(u))));

def get_confidence_intervals(df : pd.DataFrame, confidence, x : str, y : str):
    # AI Generation Disclaimer

    def calculate_ci(group):
        n = len(group)
        if n < 2:
            return pd.Series({'mean': group.mean(), 'lower': np.nan, 'upper': np.nan})
        
        mean = np.mean(group)
        sem = stats.sem(group) # Standard Error of the Mean
        
        # Calculate the interval using the t-distribution
        h = sem * stats.t.ppf((1 + confidence) / 2., n - 1)
        
        return pd.Series({
            'mean': mean,
            'lower': mean - h,
            'upper': mean + h,
            'count': n
        })

    result = df.groupby(x)[y].apply(calculate_ci).unstack()
    return result