# data_processing/resample_data.py

import sqlite3
import pandas as pd
from config.settings import DB_PATH

def load_ticks(symbol):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT ts, price, size, side FROM ticks WHERE symbol = ?",
        conn,
        params=(symbol,)
    )
    conn.close()

    if df.empty:
        return df

    # FIX: handle mixed timestamp formats
    df["ts"] = pd.to_datetime(df["ts"], format="mixed", errors="coerce")
    
    # Ensure UTC awareness
    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize("UTC")
    else:
        df["ts"] = df["ts"].dt.tz_convert("UTC")

    df = df.dropna(subset=["ts"])
    df.set_index("ts", inplace=True)
    return df

def resample_prices(df, timeframe):
    return df["price"].resample(timeframe).last().dropna()
