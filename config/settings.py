# config/settings.py

SYMBOLS = ["btcusdt", "ethusdt"]


DB_PATH = "database/ticks.db"


TIMEFRAMES = {
    "1s": "1S",
    "1m": "1T",
    "5m": "5T"
}


Z_SCORE_ALERT_THRESHOLD = 2.0
