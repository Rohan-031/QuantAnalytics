# data_processing/analytics.py

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

def calculate_ols_hedge_ratio(series_y, series_x):
    """
    Calculates the hedge ratio (beta) using OLS regression: Y = beta * X + alpha
    """
    if len(series_y) != len(series_x) or len(series_y) < 2:
        return 0.0
    
    x = sm.add_constant(series_x)
    model = sm.OLS(series_y, x).fit()
    return model.params[1] # beta

def calculate_spread(series_y, series_x, hedge_ratio):
    """
    Calculates the spread: Spread = Y - (Hedge Ratio * X)
    """
    return series_y - (hedge_ratio * series_x)

def perform_adf_test(series):
    """
    Performs Augmented Dickey-Fuller test for stationarity.
    Returns: p-value, is_stationary (bool)
    """
    if len(series) < 30: # ADF requires sufficient data
        return 1.0, False
        
    try:
        result = adfuller(series)
        p_value = result[1]
        return p_value, p_value < 0.05
    except:
        return 1.0, False

def calculate_rolling_correlation(series_y, series_x, window=60):
    return series_y.rolling(window=window).corr(series_x)
