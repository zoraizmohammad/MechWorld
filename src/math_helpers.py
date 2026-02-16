from scipy import stats
import pandas as pd
import numpy as np

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