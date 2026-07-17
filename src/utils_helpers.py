from scipy import stats
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Union, Iterable
import re
import os

PROJECT_ROOT_DIR = os.path.join(os.path.dirname(__file__),"..")

def regex_network_files(jobid : Union[int,None], size : Union[int,None], rho_0 : Union[float,None], isotropy : Union[float,None], extension : str = "out") -> str:
    if jobid:
        regex_pattern = "job"+str(jobid)+r".*"
    else:
        regex_pattern = r".*"

    if size:
        regex_pattern += r"dsu"+str(size)+r".*";
    if rho_0:
        regex_pattern += r"rho"+str(rho_0)+r".*";
    if isotropy:
        regex_pattern += r"a"+str(int(100*isotropy))+r".*";
    return regex_pattern + r"\." + extension

def add_curve_with_ci(df, x_name, y_name, curve_linestyle = "-", curve_color = "black", curve_label_override = None, ax : plt.Axes = None):

    if curve_label_override == None:
        label_str = None;
    else:
        label_str = curve_label_override;
    
    ci_df = get_confidence_intervals(df, 0.95, x_name, y_name);
    n = int(len(df)/len(ci_df))
    
    if ax:
        ax.plot(ci_df.index, ci_df['mean'], color=curve_color, linestyle=curve_linestyle, label=label_str)
        ax.fill_between(
            ci_df.index,
            ci_df['lower'],
            ci_df['upper'],
            color=curve_color, 
            alpha=0.2
        ) 
    else:
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
        return float(rho_0_str);
    else:
        return float(rho_0_str)/100;

def get_crosslinkage_from_filename(filename : str) -> float:
    link_str_match = re.match(r".+_link(0\.+\d+).+",filename);
    if link_str_match:
        return float(link_str_match.group(1));
    else:
        return None;

def apply_band_filters_to_df(df, bandpass_filters : Iterable[tuple[float,str,float]]):
    if not bandpass_filters:
        return df;

    for filter_tuple in bandpass_filters:
        if not filter_tuple:
            continue

        min_allowed, column_label, max_allowed = filter_tuple;
        mask = (df[column_label] >= min_allowed) & (df[column_label] <= max_allowed)
        return df[mask];

def flory_schulz_mean_length(a : Union[str,float]):
    return 2/(1-float(a))-1;

def bucket_round(data : float, to : float) -> float:
    return np.round(data / to) * to;

def get_angle_between_vectors(v, u):
    return np.rad2deg(np.arccos(np.dot(v, u) / (np.linalg.norm(v)*np.linalg.norm(u))));

def get_confidence_intervals(df : pd.DataFrame, confidence, x : str, y : str):
    # AI Generation Disclaimer

    def calculate_ci(group):
        n = len(group)
        if n < 2:
            return pd.Series({'mean': group.mean(), 'lower': np.nan, 'upper': np.nan, 'count':1})
        
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

    if len(df) == 0:
        return pd.Series({'mean': np.nan, 'lower': np.nan, 'upper': np.nan})

    result = df.groupby(x)[y].apply(calculate_ci).unstack()
    return result