# data_ingestion/binance_ws.py

import json
import threading
import websocket
from datetime import datetime

from config.settings import SYMBOLS
from data_storage.sqlite_db import create_ticks_table, insert_tick
from utils.logger import logger

def normalize_tick(data):
    ts = datetime.utcfromtimestamp(
        (data.get("T") or data.get("E")) / 1000
    ).isoformat()
    
    # "m": true -> Is the buyer the market maker? -> SELL order hit the bid
    # "m": false -> BUY order lifted the offer
    side = "SELL" if data["m"] else "BUY"

    return {
        "symbol": data["s"].lower(),
        "ts": ts,
        "price": float(data["p"]),
        "size": float(data["q"]),
        "side": side
    }

def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("e") == "trade":
            tick = normalize_tick(data)
            insert_tick(
                tick["ts"],
                tick["symbol"],
                tick["price"],
                tick["size"],
                tick["side"]
            )
            logger.info(f"Saved tick: {tick}")
    except Exception as e:
        logger.error(f"Error processing tick: {e}")

def start_binance_stream():
    create_ticks_table()

    def run():
        streams = "/".join([f"{s}@trade" for s in SYMBOLS])
        url = f"wss://fstream.binance.com/ws/{streams}"

        ws = websocket.WebSocketApp(
            url,
            on_message=on_message
        )

        logger.info("Starting Binance Futures WebSocket...")
        ws.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
