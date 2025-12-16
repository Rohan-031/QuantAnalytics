# analytics/basic_stats.py

import pandas as pd

def compute_rolling_stats(series, window):
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    return rolling_mean, rolling_std

def compute_zscore(series, window):
    mean, std = compute_rolling_stats(series, window)
    zscore = (series - mean) / std
    return zscore
