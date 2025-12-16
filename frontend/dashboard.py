import streamlit as st
import time
import pandas as pd
import altair as alt

from data_processing.resample_data import load_ticks, resample_prices
from analytics.basic_stats import compute_zscore, compute_rolling_stats
from data_processing.analytics import calculate_ols_hedge_ratio, calculate_spread, perform_adf_test, calculate_rolling_correlation
from config.settings import TIMEFRAMES, SYMBOLS

def load_css():
    with open("frontend/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_metric_card(title, value, delta=None, help_text=None):
    delta_html = ""
    if delta:
        color = "#00c851" if delta > 0 else "#ff4b4b"
        icon = "↑" if delta > 0 else "↓"
        delta_html = f"<span style='color:{color}; font-size: 0.9rem; margin-left: 10px'>{icon} {abs(delta):.2f}%</span>"
    
    tooltip_html = f'title="{help_text}"' if help_text else ""
    
    st.markdown(f"""
    <div class="metric-card" {tooltip_html}>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value} {delta_html}</div>
        {'<div class="metric-help" style="font-size:0.7rem; color:#888; margin-top:4px">' + help_text + '</div>' if help_text else ''}
    </div>
    """, unsafe_allow_html=True)

def auto_adjust_window(timeframe, user_window):
    """Auto-adjust window size based on timeframe to ensure relevance."""
    if timeframe == "1s":
        return max(user_window, 60) # At least 60s for 1s
    elif timeframe == "1m":
        return max(user_window, 30) # At least 30m for 1m
    return user_window

def render_market_status(z_score):
    """Renders a simplified traffic-light status banner."""
    abs_z = abs(z_score)
    if abs_z < 1.5:
        status = "NORMAL"
        color = "#00c851" # Green
        msg = "Market behavior is within expected range."
    elif 1.5 <= abs_z < 2.5:
        status = "WATCH"
        color = "#ffbb33" # Orange/Yellow
        msg = "Volatility is elevated. Monitor for potential anomalies."
    else: # >= 2.5
        status = "ALERT"
        color = "#ff4b4b" # Red
        msg = "Significant price deviation detected! (Potential mean reversion or breakout)."
        
    st.markdown(f"""
    <div style="padding: 15px; border-radius: 8px; background-color: {color}20; border-left: 5px solid {color}; margin-bottom: 20px;">
        <div style="font-size: 1.2rem; font-weight: bold; color: {color};">● MARKET STATUS: {status}</div>
        <div style="color: #ddd;">{msg}</div>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    load_css()
    st.markdown("# ⚡ QuantAnalytics <span style='font-size:1.0rem; color:#888'>| Live Monitor</span>", unsafe_allow_html=True)

    # --- SIDEBAR CONFIG ---
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        tf_label = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=0)
        user_window = st.slider("Rolling Window (Samples)", 20, 200, 50, help="Number of bars used for Z-Score and Moving Average")
        refresh_sec = st.slider("Refresh Rate", 1, 10, 2)
        
        st.markdown("---")
        st.markdown("### 📊 Export")
        download_container = st.empty()
        
        st.markdown("---")
        st.caption(f"v1.2.0 | Connected: {len(SYMBOLS)} Pairs")

    # --- DATA LOADING ---
    tf = TIMEFRAMES[tf_label]
    window = auto_adjust_window(tf_label, user_window)
    
    sym1, sym2 = SYMBOLS[0], SYMBOLS[1] # Primary (BTC), Secondary (ETH)
    df1 = load_ticks(sym1)
    df2 = load_ticks(sym2)

    # Check for minimal data existence
    if df1.empty or df2.empty:
        download_container.text("⏳ Waiting for feed...")
        st.info("📡 Connecting to Binance WebSocket... Waiting for initial ticks.")
        time.sleep(refresh_sec)
        st.rerun()
        return

    # Filter recent history (keep 3x window to show context, but keep it light)
    lookback = window * 3
    # Approximate lookback based on rows is tricky with ticks, so we use time
    # But for resampling, we need enough raw data. Let's just keep last 20m for safety.
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(minutes=30)
    df1 = df1[df1.index >= cutoff]
    df2 = df2[df2.index >= cutoff]

    # Resample
    p1 = resample_prices(df1, tf)
    p2 = resample_prices(df2, tf)
    
    # Ensure sufficient resampled data
    if len(p1) < window:
        download_container.text(f"⏳ Building history ({len(p1)}/{window})...")
        st.warning(f"Building history for {tf_label} interval... ({len(p1)}/{window} bars collected)")
        time.sleep(refresh_sec)
        st.rerun()
        return

    # --- TABS LAYOUT ---
    tab_monitor, tab_pair, tab_diag = st.tabs(["📉 Price Monitor", "⚖️ Pair Trading", "🔍 Diagnostics"])

    # --- SHARED CALCULATIONS ---
    # Metrics for Primary Symbol
    price_val = p1.iloc[-1]
    
    # Volume Calc (Last 30 bars sum approx)
    recent_vol = df1[df1.index >= (df1.index.max() - pd.Timedelta(minutes=5))].copy()
    vol_stats = recent_vol.groupby("side")["size"].sum()
    buy_vol = vol_stats.get("BUY", 0.0)
    sell_vol = vol_stats.get("SELL", 0.0)
    net_flow = buy_vol - sell_vol

    # Z-Score for Primary
    zscore = compute_zscore(p1, window)
    latest_z = zscore.iloc[-1]
    mean_price, _ = compute_rolling_stats(p1, window)

    # Prepare Chart Data (Slice to last N bars for visualization)
    view_window = window * 2
    chart_df = p1.to_frame(name="price").reset_index()
    chart_df['mean'] = mean_price.values
    chart_df = chart_df.tail(view_window) # Keep visuals snappy

    # --- TAB 1: PRICE MONITOR ---
    with tab_monitor:
        render_market_status(latest_z)
        
        # Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1: render_metric_card(f"{sym1.upper()} Price", f"${price_val:,.2f}", help_text="Latest traded price")
        with m2: render_metric_card("Net Flow (5m)", f"{net_flow:+,.2f}", delta=None, help_text="Net Buy Vol - Sell Vol over last 5 mins")
        with m3: render_metric_card("Z-Score", f"{latest_z:.2f}", delta=None, help_text="Standard deviations from the mean")
        with m4: render_metric_card("Buy/Sell Vol", f"{buy_vol:.0f} / {sell_vol:.0f}", delta=None, help_text="Total Volume (Base Asset) in last 5m")

        # Main Price Chart
        col_main, col_side = st.columns([3, 1])
        with col_main:
            st.markdown("### Price Action")
            base = alt.Chart(chart_df).encode(x=alt.X('ts:T', axis=alt.Axis(format='%H:%M:%S', title=None)))
            line = base.mark_line(color='#00f260').encode(
                y=alt.Y('price:Q', scale=alt.Scale(zero=False), title="Price"),
                tooltip=['ts', 'price']
            )
            ma = base.mark_line(color='#0575e6', strokeDash=[5,5]).encode(y='mean:Q')
            st.altair_chart((line + ma).properties(height=350), use_container_width=True)
            st.caption("Green: Price | Blue Dashed: Moving Average")
        
        with col_side:
            st.markdown("### Vol Dist")
            # Resample volume for bar chart
            v_resampled = df1.resample(tf)["size"].sum().tail(view_window).reset_index()
            if not v_resampled.empty:
                bar = alt.Chart(v_resampled).mark_bar(color='#a29bfe').encode(
                    x=alt.X('ts:T', axis=None),
                    y=alt.Y('size:Q', title=None),
                    tooltip=['ts', 'size']
                ).properties(height=350)
                st.altair_chart(bar, use_container_width=True)
            else:
                st.write("No vol data")

    # --- TAB 2: PAIR TRADING ---
    with tab_pair:
        # Align Data
        aligned_df = pd.concat([p1, p2], axis=1, keys=[sym1, sym2]).dropna()
        
        if len(aligned_df) < window:
            st.warning(f"Collecting pair data... ({len(aligned_df)}/{window})")
        else:
            # Pair Calcs
            y, x = aligned_df[sym1], aligned_df[sym2]
            try:
                # Hedge Ratio
                hedge_ratio = calculate_ols_hedge_ratio(y, x)
                # Spread
                spread = calculate_spread(y, x, hedge_ratio)
                zscore_spread = compute_zscore(spread, window)
                latest_spread_z = zscore_spread.iloc[-1]
                # ADF
                adf_p, is_stationary = perform_adf_test(spread.dropna())
            except Exception as e:
                st.error(f"Analytics Error: {e}")
                return

            # Pair Stats Header
            st.markdown(f"#### {sym1.upper()} / {sym2.upper()} Analysis")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Hedge Ratio (β)", f"{hedge_ratio:.4f}", help=f"For every 1 unit of {sym2}, hold {hedge_ratio:.2f} of {sym1}")
            s2.metric("Spread Z-Score", f"{latest_spread_z:.2f}", help="Deviation of the spread from its mean")
            s3.metric("Stationary (ADF)", "YES" if is_stationary else "NO", help=f"Is the spread mean-reverting? (p-value: {adf_p:.3f})", delta_color="normal" if is_stationary else "inverse")
            
            # Scatter Plot
            st.write("---")
            c_spread, c_scatter = st.columns([2, 1])
            
            with c_spread:
                st.markdown("##### Spread Z-Score History")
                z_data = zscore_spread.tail(view_window).to_frame(name="zscore").reset_index()
                
                base_z = alt.Chart(z_data).encode(x=alt.X('ts:T', axis=alt.Axis(format='%H:%M:%S', title=None)))
                area_z = base_z.mark_area(
                    line={'color':'#ff00ff'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='rgba(255, 0, 255, 0.5)', offset=0),
                               alt.GradientStop(color='rgba(255, 0, 255, 0.05)', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(y='zscore:Q')
                
                rule_top = alt.Chart(pd.DataFrame({'y': [2]})).mark_rule(color='red', strokeDash=[3,3]).encode(y='y')
                rule_bot = alt.Chart(pd.DataFrame({'y': [-2]})).mark_rule(color='red', strokeDash=[3,3]).encode(y='y')
                
                st.altair_chart((area_z + rule_top + rule_bot).properties(height=300), use_container_width=True)

            with c_scatter:
                st.markdown("##### Correlation")
                corr_data = pd.DataFrame({'Y': y, 'X': x}).tail(window)
                scatter = alt.Chart(corr_data).mark_circle(size=60, opacity=0.6).encode(
                    x=alt.X('X', scale=alt.Scale(zero=False), title=sym2),
                    y=alt.Y('Y', scale=alt.Scale(zero=False), title=sym1),
                    tooltip=['X', 'Y']
                ).properties(height=300)
                st.altair_chart(scatter, use_container_width=True)

            # Export Button Logic (populate container in sidebar)
            export_df = aligned_df.copy()
            export_df['spread'] = spread
            export_df['z_score_spread'] = zscore_spread
            csv = export_df.to_csv().encode('utf-8')
            download_container.download_button("📥 Download Data", csv, "quant_data.csv", "text/csv")

    # --- TAB 3: DIAGNOSTICS ---
    with tab_diag:
        st.markdown("### System Health")
        d1, d2 = st.columns(2)
        d1.info(f"Loaded {len(df1)} ticks for {sym1}")
        d2.info(f"Loaded {len(df2)} ticks for {sym2}")
        
        st.subheader("Raw Data Preview")
        st.dataframe(df1.sort_index(ascending=False).head(10), use_container_width=True)

    # Auto Refresh
    time.sleep(refresh_sec)
    st.rerun()
