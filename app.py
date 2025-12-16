# app.py

import streamlit as st
from data_ingestion.binance_ws import start_binance_stream
from frontend.dashboard import render_dashboard

st.set_page_config(
    page_title="QuantAnalytics | Pro",
    page_icon="⚡",
    layout="wide"
)

def main():
    # Start WebSocket ONLY once
    if "ws_started" not in st.session_state:
        start_binance_stream()
        st.session_state.ws_started = True

    render_dashboard()

if __name__ == "__main__":
    main()
