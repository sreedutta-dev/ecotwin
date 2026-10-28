"""
EcoTwin: Smart Environment Dashboard (Digital Twin Project)
Run with:  streamlit run dashboard.py

Sensor data is simulated here. To use real hardware (Arduino / ESP32 / Raspberry Pi),
replace `next_reading()` with code that reads from your serial port / MQTT / API.
"""
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------ page setup
st.set_page_config(page_title="EcoTwin Dashboard", page_icon="🌿", layout="wide")

BG, CARD, BORDER = "#0a1220", "#0f1b2e", "#1b2b45"
C_TEMP, C_HUM, C_SOIL, C_LIGHT = "#3ddc4a", "#2d9cff", "#ff7a1a", "#ffc800"

st.markdown(
    f"""
<style>
.stApp {{ background:{BG}; color:#e8eefc; }}
header[data-testid="stHeader"] {{ background:transparent; }}
section[data-testid="stSidebar"] {{ background:#08101d; border-right:1px solid {BORDER}; }}
.block-container {{ padding-top:1.5rem; max-width:1500px; }}
.card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:10px; padding:14px 16px; margin-bottom:12px; }}
.card h4 {{ margin:0 0 8px 0; font-size:15px; font-weight:600; color:#e8eefc; }}
.metric {{ display:flex; align-items:center; gap:14px; }}
.icon {{ width:52px; height:52px; border-radius:50%; display:flex; align-items:center;
        justify-content:center; font-size:26px; }}
.m-label {{ font-size:14px; color:#cfd8ee; }}
.m-value {{ font-size:32px; font-weight:700; line-height:1.1; }}
.m-unit {{ font-size:18px; font-weight:400; color:#cfd8ee; }}
.m-delta {{ font-size:12px; color:#8da0c4; }}
.up {{ color:#3ddc4a; }} .down {{ color:#ff5a4d; }}
.stat-row {{ display:flex; justify-content:space-between; padding:7px 0; font-size:13px; }}
.alert {{ border-radius:8px; padding:9px 12px; font-size:12px; margin-top:6px; }}
.alert.warn {{ background:#2a1f10; border:1px solid #a65a12; color:#ffb35c; }}
.alert.ok {{ background:#0e2a22; border:1px solid #1f6b4f; color:#4be0a0; }}
.reco {{ border-radius:8px; padding:9px 12px; margin-bottom:8px; font-size:12px; }}
.reco b {{ font-size:13px; display:block; }}
.reco.warn {{ background:#2a2010; border:1px solid #a67812; color:#f1d9a0; }}
.reco.ok {{ background:#0d2a1f; border:1px solid #1f6b4f; color:#bfe9d3; }}
table.log {{ width:100%; border-collapse:collapse; font-size:13px; }}
table.log th {{ background:#14243b; padding:8px; text-align:center; font-weight:500; }}
table.log td {{ padding:8px; text-align:center; border-bottom:1px solid {BORDER}; }}
.status-dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; background:#3ddc4a; margin-right:6px; }}
.logo {{ font-size:26px; font-weight:700; color:#3ddc4a; }}
.logo small {{ display:block; font-size:12px; color:#8da0c4; font-weight:400; }}
div[role="radiogroup"] label {{ padding:8px 10px; border-radius:8px; }}
div[role="radiogroup"] label:hover {{ background:#0f2a22; }}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ data layer
SENSORS = ["Temperature", "Humidity", "Soil Moisture", "Light"]


def next_reading(prev: dict | None, rng: np.random.Generator) -> dict:
    """Simulate one sensor reading. Replace with real sensor code if you have hardware."""
    if prev is None:
        prev = dict(Temperature=26.0, Humidity=72.0, **{"Soil Moisture": 55.0}, Light=800.0)
    temp = prev["Temperature"] + 0.1 * (26 - prev["Temperature"]) + rng.normal(0, 0.25)
    hum = prev["Humidity"] + 0.1 * (72 - prev["Humidity"]) + rng.normal(0, 0.8)
    soil = prev["Soil Moisture"] - 0.15 + rng.normal(0, 0.3)
    if soil < 25:  # simulate the plants being watered
        soil = rng.uniform(55, 65)
    light = prev["Light"] + 0.1 * (800 - prev["Light"]) + rng.normal(0, 25)
    return {
        "Temperature": round(temp, 1),
        "Humidity": round(float(np.clip(hum, 0, 100)), 0),
        "Soil Moisture": round(float(np.clip(soil, 0, 100)), 0),
        "Light": round(float(np.clip(light, 0, 1500)), 0),
    }


def init_state():
    if "df" in st.session_state:
        return
    rng = np.random.default_rng(42)
    now = datetime.now().replace(second=0, microsecond=0)
    rows, prev = [], None
    for i in range(24 * 60, 0, -1):  # 24 hours of 1-minute history
        prev = next_reading(prev, rng)
        rows.append({"Time": now - timedelta(minutes=i), **prev})
    st.session_state.df = pd.DataFrame(rows)
    st.session_state.rng = rng
    st.session_state.settings = {
        "temp_min": 20.0, "temp_max": 30.0,
        "hum_min": 40, "hum_max": 80,
        "soil_low": 40,
        "light_min": 300, "light_max": 1000,
    }


def add_reading():
    df = st.session_state.df
    last = df.iloc[-1][SENSORS].to_dict()
    new = next_reading(last, st.session_state.rng)
    row = pd.DataFrame([{"Time": datetime.now(), **new}])
    st.session_state.df = pd.concat([df, row], ignore_index=True).tail(5000)


# ------------------------------------------------------------------ analytics
def health_score(r: dict, s: dict) -> int:
    def sub(v, lo, hi):
        if lo <= v <= hi:
            return 100
        d = (lo - v) if v < lo else (v - hi)
        return max(0, 100 - 100 * d / (hi - lo))

    scores = [
        sub(r["Temperature"], s["temp_min"], s["temp_max"]),
        sub(r["Humidity"], s["hum_min"], s["hum_max"]),
        sub(r["Soil Moisture"], s["soil_low"], 80),
        sub(r["Light"], s["light_min"], s["light_max"]),
    ]
    return int(round(np.mean(scores)))


def minutes_until_dry(df: pd.DataFrame, threshold: float = 20.0):
    """Linear-regression prediction of when soil moisture hits `threshold`."""
    recent = df.tail(60)
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent["Soil Moisture"].values, 1)
    if slope >= -0.001:
        return None
    return int(max(0, (threshold - recent["Soil Moisture"].iloc[-1]) / slope))


def recommendations(r: dict, s: dict):
    out = []
    if r["Soil Moisture"] < s["soil_low"]:
        out.append(("warn", "💧", "Water Plants Soon", "Soil moisture is low. Consider watering the plants."))
    else:
        out.append(("ok", "💧", "Soil Moisture Good", "Soil moisture is at a healthy level."))
    if r["Light"] < s["light_min"]:
        out.append(("warn", "☀️", "Low Light", "Move plants to a brighter spot or add grow lights."))
    elif r["Light"] > s["light_max"]:
        out.append(("warn", "☀️", "Too Much Light", "Consider providing some shade."))
    else:
        out.append(("ok", "☀️", "Good Light Levels", "Light intensity is optimal for plants."))
    if r["Temperature"] > s["temp_max"]:
        out.append(("warn", "🌡️", "Temperature High", "Ventilate or cool the environment."))
    elif r["Temperature"] < s["temp_min"]:
        out.append(("warn", "🌡️", "Temperature Low", "Consider warming the environment."))
    else:
        out.append(("ok", "🌡️", "Temperature Normal", "Temperature is in a good range."))
    if r["Humidity"] > s["hum_max"] or r["Humidity"] < s["hum_min"]:
        out.append(("warn", "💦", "Humidity Off", "Humidity is outside the ideal range."))
    else:
        out.append(("ok", "💦", "Humidity Normal", "Humidity levels are good."))
    return out


# ------------------------------------------------------------------ UI pieces
def plot_layout(fig, height=300, **kw):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfd8ee", size=11),
        legend=dict(orientation="h", y=1.15, x=0), **kw,
    )
    fig.update_xaxes(gridcolor="#16263f", zeroline=False)
    fig.update_yaxes(gridcolor="#16263f", zeroline=False)
    return fig


def metric_card(icon, bg, label, value, unit, delta, delta_unit):
    cls = "up" if delta >= 0 else "down"
    arrow = "↑" if delta >= 0 else "↓"
    st.markdown(
        f"""<div class="card"><div class="metric">
        <div class="icon" style="background:{bg}">{icon}</div>
        <div><div class="m-label">{label}</div>
        <div class="m-value">{value}<span class="m-unit"> {unit}</span></div>
        <div class="m-delta"><span class="{cls}">{arrow} {abs(delta):g} {delta_unit}</span> from last reading</div>
        </div></div></div>""",
        unsafe_allow_html=True,
    )


def metrics_row(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    c = st.columns(4)
    with c[0]:
        metric_card("🌡️", "#3a1f1c", "Temperature", f"{last.Temperature:.1f}", "°C",
                    round(last.Temperature - prev.Temperature, 1), "°C")
    with c[1]:
        metric_card("💧", "#0f2a4a", "Humidity", f"{last.Humidity:.0f}", "%",
                    last.Humidity - prev.Humidity, "%")
    with c[2]:
        metric_card("🌱", "#2b2d10", "Soil Moisture", f"{last['Soil Moisture']:.0f}", "%",
                    last["Soil Moisture"] - prev["Soil Moisture"], "%")
    with c[3]:
        metric_card("☀️", "#2d2a0e", "Light Intensity", f"{last.Light:.0f}", "lux",
                    last.Light - prev.Light, "lux")


def line_chart(df, height=300, minutes=60):
    d = df[df.Time >= df.Time.max() - timedelta(minutes=minutes)]
    fig = go.Figure()
    series = [("Temperature", "Temperature (°C)", C_TEMP, 1), ("Humidity", "Humidity (%)", C_HUM, 1),
              ("Soil Moisture", "Soil Moisture (%)", C_SOIL, 1), ("Light", "Light (lux)", C_LIGHT, 1 / 20)]
    for col, name, color, scale in series:  # light is scaled /20 so it shares the 0-100 axis
        fig.add_trace(go.Scatter(x=d.Time, y=d[col] * scale, name=name, mode="lines",
                                 line=dict(color=color, width=2), customdata=d[col],
                                 hovertemplate="%{customdata}<extra>" + name + "</extra>"))
    plot_layout(fig, height)
    fig.update_yaxes(range=[0, 100])
    return fig


def trend_chart(df, col, color, height=190):
    d = df[df.Time >= datetime.now().replace(hour=0, minute=0, second=0)]
    if len(d) < 5:
        d = df.tail(120)
    fig = go.Figure(go.Scatter(x=d.Time, y=d[col], mode="lines", line=dict(color=color, width=2)))
    plot_layout(fig, height, showlegend=False)
    fig.update_yaxes(range=[0, 100] if col != "Temperature" else None)
    return fig


def health_gauge(score):
    color = "#3ddc4a" if score >= 75 else "#ffc800" if score >= 50 else "#ff5a4d"
    fig = go.Figure(go.Pie(values=[score, 100 - score], hole=0.78, direction="clockwise", sort=False,
                           marker=dict(colors=[color, "#16263f"]), textinfo="none", hoverinfo="skip"))
    fig.add_annotation(text=f"<b style='font-size:38px'>{score}</b><br>/100", showarrow=False)
    fig.update_layout(height=210, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e8eefc"))
    return fig, color


def log_table(df, n=5):
    rows = ""
    for _, r in df.tail(n)[::-1].iterrows():
        rows += (f"<tr><td>{r.Time:%d %b %Y %H:%M:%S}</td><td>{r.Temperature}</td>"
                 f"<td>{r.Humidity:.0f}</td><td>{r['Soil Moisture']:.0f}</td><td>{r.Light:.0f}</td></tr>")
    st.markdown(
        f"""<div class="card"><h4>Live Data Log <span style="font-weight:400;color:#8da0c4">
        (Latest {n} Records)</span></h4><table class="log"><tr><th>Time</th><th>Temperature (°C)</th>
        <th>Humidity (%)</th><th>Soil Moisture (%)</th><th>Light (lux)</th></tr>{rows}</table></div>""",
        unsafe_allow_html=True,
    )


def stats_card(df):
    today = df[df.Time >= datetime.now().replace(hour=0, minute=0, second=0)]
    if len(today) < 5:
        today = df.tail(1440)
    items = [
        ("🌡️", "Avg Temperature", f"{today.Temperature.mean():.1f} °C", C_TEMP),
        ("🔥", "Max Temperature", f"{today.Temperature.max():.1f} °C", "#ff7a4d"),
        ("❄️", "Min Temperature", f"{today.Temperature.min():.1f} °C", "#4da6ff"),
        ("💧", "Avg Humidity", f"{today.Humidity.mean():.0f} %", C_HUM),
        ("🌱", "Min Soil Moisture", f"{today['Soil Moisture'].min():.0f} %", C_SOIL),
        ("☀️", "Max Light", f"{today.Light.max():.0f} lux", C_LIGHT),
    ]
    html = "".join(f'<div class="stat-row"><span>{i} {n}</span><b style="color:{c}">{v}</b></div>'
                   for i, n, v, c in items)
    st.markdown(f'<div class="card"><h4>Statistics (Today)</h4>{html}</div>', unsafe_allow_html=True)


def reco_card(r, s, limit=None):
    items = recommendations(r, s)[:limit]
    html = "".join(f'<div class="reco {k}"><b>{i} {t}</b>{d}</div>' for k, i, t, d in items)
    st.markdown(f'<div class="card"><h4>Recommendations</h4>{html}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ pages
def page_dashboard(minutes):
    df, s = st.session_state.df, st.session_state.settings
    last = df.iloc[-1][SENSORS].to_dict()
    metrics_row(df)

    left, right = st.columns([2.6, 1])
    with left:
        st.markdown('<div class="card"><h4>Sensor Readings Over Time</h4>', unsafe_allow_html=True)
        st.plotly_chart(line_chart(df, 300, minutes), use_container_width=True, key=f"main{time.time()}")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        score = health_score(last, s)
        fig, color = health_gauge(score)
        label = "Good" if score >= 75 else "Fair" if score >= 50 else "Poor"
        st.markdown('<div class="card"><h4>Environmental Health Score</h4>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key=f"gauge{time.time()}")
        st.markdown(
            f'<div style="text-align:center"><span style="background:{color}33;color:{color};'
            f'padding:2px 18px;border-radius:6px">{label}</span><br>'
            f'<small style="color:{color}">🌿 Your environment is {"healthy" if score >= 75 else "at risk"}!</small></div></div>',
            unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1.15, 1.15, 1])
    with c1:
        stats_card(df)
    with c2:
        st.markdown('<div class="card"><h4>Soil Moisture Trend (Today)</h4>', unsafe_allow_html=True)
        st.plotly_chart(trend_chart(df, "Soil Moisture", C_SOIL), use_container_width=True, key=f"soil{time.time()}")
        eta = minutes_until_dry(df)
        if eta is not None:
            st.markdown(f'<div class="alert warn">⚠️ Soil moisture is decreasing.<br>'
                        f'It may become dry in ~{eta} minutes.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert ok">Soil moisture is stable.</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><h4>Temperature Trend (Today)</h4>', unsafe_allow_html=True)
        st.plotly_chart(trend_chart(df, "Temperature", C_TEMP), use_container_width=True, key=f"temp{time.time()}")
        st.markdown('<div class="alert ok">↗ Temperature is stable.<br>No heat stress for plants.</div></div>',
                    unsafe_allow_html=True)
    with c4:
        reco_card(last, s)

    a, b = st.columns([2.6, 1])
    with a:
        log_table(df)
    with b:
        st.markdown('<div class="card" style="text-align:center;font-size:54px;padding:22px">🌳🏡🏭<br>'
                    '<span style="font-size:12px;color:#8da0c4">Your miniature smart environment</span></div>',
                    unsafe_allow_html=True)


def page_live(minutes):
    metrics_row(st.session_state.df)
    log_table(st.session_state.df, 15)


def page_graphs(minutes):
    df = st.session_state.df
    for col, color in [("Temperature", C_TEMP), ("Humidity", C_HUM), ("Soil Moisture", C_SOIL), ("Light", C_LIGHT)]:
        d = df[df.Time >= df.Time.max() - timedelta(minutes=minutes)]
        fig = go.Figure(go.Scatter(x=d.Time, y=d[col], line=dict(color=color, width=2)))
        st.markdown(f'<div class="card"><h4>{col}</h4>', unsafe_allow_html=True)
        st.plotly_chart(plot_layout(fig, 220, showlegend=False), use_container_width=True, key=f"g{col}{time.time()}")
        st.markdown("</div>", unsafe_allow_html=True)


def page_analytics(minutes):
    df = st.session_state.df
    stats_card(df)
    corr = df[SENSORS].corr().round(2)
    fig = go.Figure(go.Heatmap(z=corr.values, x=SENSORS, y=SENSORS, colorscale="Viridis",
                               text=corr.values, texttemplate="%{text}"))
    st.markdown('<div class="card"><h4>Sensor Correlation</h4>', unsafe_allow_html=True)
    st.plotly_chart(plot_layout(fig, 350), use_container_width=True, key=f"corr{time.time()}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.dataframe(df[SENSORS].describe().round(2), use_container_width=True)


def page_predictions(minutes):
    df = st.session_state.df
    recent = df.tail(120)
    x = np.arange(len(recent))
    fig = go.Figure()
    for col, color in [("Temperature", C_TEMP), ("Soil Moisture", C_SOIL), ("Humidity", C_HUM)]:
        m, b = np.polyfit(x, recent[col].values, 1)
        fx = np.arange(len(recent), len(recent) + 30)
        ft = [recent.Time.iloc[-1] + timedelta(minutes=int(i - len(recent) + 1)) for i in fx]
        fig.add_trace(go.Scatter(x=recent.Time, y=recent[col], name=col, line=dict(color=color)))
        fig.add_trace(go.Scatter(x=ft, y=m * fx + b, name=f"{col} (forecast)", line=dict(color=color, dash="dash")))
    st.markdown('<div class="card"><h4>30-minute Linear Forecast</h4>', unsafe_allow_html=True)
    st.plotly_chart(plot_layout(fig, 400), use_container_width=True, key=f"pred{time.time()}")
    st.markdown("</div>", unsafe_allow_html=True)
    eta = minutes_until_dry(df)
    st.info(f"Soil will reach 20% in ~{eta} minutes." if eta else "Soil moisture is stable – no dry-out predicted.")


def page_reco(minutes):
    reco_card(st.session_state.df.iloc[-1][SENSORS].to_dict(), st.session_state.settings)


def page_log(minutes):
    df = st.session_state.df
    st.dataframe(df.iloc[::-1], use_container_width=True, height=500)
    st.download_button("⬇ Download CSV", df.to_csv(index=False), "ecotwin_log.csv", "text/csv")


def page_settings(minutes):
    s = st.session_state.settings
    st.subheader("Ideal ranges & alert thresholds")
    c = st.columns(2)
    s["temp_min"], s["temp_max"] = c[0].slider("Temperature range (°C)", 0.0, 50.0, (s["temp_min"], s["temp_max"]))
    s["hum_min"], s["hum_max"] = c[1].slider("Humidity range (%)", 0, 100, (s["hum_min"], s["hum_max"]))
    s["soil_low"] = c[0].slider("Water alert when soil moisture below (%)", 0, 100, s["soil_low"])
    s["light_min"], s["light_max"] = c[1].slider("Light range (lux)", 0, 2000, (s["light_min"], s["light_max"]))


def page_about(minutes):
    st.markdown("""
### 🌿 EcoTwin – Digital Twin Project
EcoTwin mirrors a miniature smart environment (plants, soil, climate and lighting) as a **digital twin**.
It collects temperature, humidity, soil-moisture and light readings, visualises them live,
scores the environment's health, predicts when plants will need water, and gives recommendations.

**Stack:** Python · Streamlit · Plotly · Pandas · NumPy
""")


PAGES = {
    "Dashboard": ("🏠", page_dashboard), "Live Data": ("📈", page_live), "Graphs": ("📊", page_graphs),
    "Analytics": ("🥧", page_analytics), "Predictions": ("📉", page_predictions),
    "Recommendations": ("💡", page_reco), "Data Log": ("📋", page_log),
    "Settings": ("⚙️", page_settings), "About Project": ("ℹ️", page_about),
}

# ------------------------------------------------------------------ main
init_state()

with st.sidebar:
    st.markdown('<div class="logo">🌿 EcoTwin<small>Digital Twin Project</small></div>', unsafe_allow_html=True)
    st.write("")
    choice = st.radio("nav", list(PAGES), label_visibility="collapsed",
                      format_func=lambda k: f"{PAGES[k][0]}  {k}")
    st.write("")
    st.markdown('<div class="card"><span class="status-dot"></span>System Status<br>'
                '<span style="color:#3ddc4a;margin-left:15px">Connected</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card" style="text-align:center;font-size:13px">{datetime.now():%I:%M:%S %p}<br>'
                f'{datetime.now():%d %b %Y}</div>', unsafe_allow_html=True)

h1, h2 = st.columns([4, 1])
h1.markdown("## EcoTwin: Smart Environment Dashboard")
h1.caption("Real-time monitoring of your miniature smart environment")
mode = h2.selectbox("Mode", ["Live Mode", "Paused"], label_visibility="collapsed")
window = st.selectbox("Range", ["Last 1 Hour", "Last 3 Hours", "Last 24 Hours"], index=0) if choice in (
    "Dashboard", "Graphs") else "Last 1 Hour"
minutes = {"Last 1 Hour": 60, "Last 3 Hours": 180, "Last 24 Hours": 1440}[window]


def render():
    if mode == "Live Mode":
        add_reading()
    PAGES[choice][1](minutes)


# auto-refresh every 5 s in live mode (needs Streamlit >= 1.37)
st.fragment(run_every=5 if mode == "Live Mode" else None)(render)()
