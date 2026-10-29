
from datetime import datetime
import random

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="EcoTwin Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_URL = "http://127.0.0.1:5000/api/sensors/readings"
POLL_SECONDS = 5
MAX_HISTORY = 500

# Light blue, green and white theme
st.markdown("""
<style>
.stApp {
    background: #f4f8fb;
    color: #17324d;
}
header[data-testid="stHeader"] {
    background: #f4f8fb;
}
.block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
}
[data-testid="stSidebar"] {
    display: none;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #dbe7f0;
    border-radius: 15px;
    padding: 18px;
    box-shadow: 0 3px 12px #17324d0a;
}
div[data-testid="stMetricLabel"] {
    color: #64748b;
}
div[data-testid="stMetricValue"] {
    color: #17324d;
}
.hero {
    background: linear-gradient(110deg, #e8f2ff, #eafaf0);
    border: 1px solid #d5e7ed;
    border-radius: 18px;
    padding: 22px 26px;
    margin-bottom: 18px;
}
.hero-title {
    font-size: 30px;
    font-weight: 750;
    color: #17324d;
}
.hero-subtitle {
    font-size: 14px;
    color: #526a80;
    margin-top: 6px;
}
.panel {
    background: white;
    border: 1px solid #dbe7f0;
    border-radius: 15px;
    padding: 15px 18px;
    margin-bottom: 14px;
}
.panel-title {
    font-size: 16px;
    font-weight: 700;
    color: #17324d;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=[
            "Time", "Soil Moisture", "Light",
            "Temperature", "Wind Speed"
        ])

    if "last_received_at" not in st.session_state:
        st.session_state.last_received_at = None

    if "api_error" not in st.session_state:
        st.session_state.api_error = None


def fetch_sensor_data():
    """Fetch actual soil moisture and light values from Flask."""
    try:
        response = requests.get(API_URL, timeout=3)
        response.raise_for_status()
        payload = response.json()

        # Support APIs that wrap their response.
        if isinstance(payload, dict) and isinstance(
            payload.get("reading"), dict
        ):
            payload = payload["reading"]

        if isinstance(payload, dict) and isinstance(
            payload.get("readings"), list
        ):
            payload = (
                payload["readings"][-1]
                if payload["readings"] else {}
            )

        if not isinstance(payload, dict) or not payload:
            st.session_state.api_error = None
            return

        soil = payload.get(
            "Soil Moisture", payload.get("soil_moisture")
        )
        light = payload.get("Light", payload.get("light"))

        if soil is None or light is None:
            raise ValueError(
                'Flask JSON must contain "Soil Moisture" and "Light".'
            )

        timestamp = payload.get(
            "received_at", payload.get("timestamp")
        )
        stamp = str(timestamp) if timestamp is not None else None

        # Do not append the same Flask reading on every refresh.
        if stamp and stamp == st.session_state.last_received_at:
            st.session_state.api_error = None
            return

        reading_time = datetime.now()
        if timestamp:
            try:
                reading_time = (
                    pd.to_datetime(timestamp, utc=True)
                    .tz_convert(None)
                    .to_pydatetime()
                )
            except Exception:
                pass

        row = {
            "Time": reading_time,
            "Soil Moisture": max(0, min(100, float(soil))),
            "Light": max(0, min(100, float(light))),

            # Mock values for demonstration only.
            "Temperature": round(random.uniform(21, 30), 1),
            "Wind Speed": round(random.uniform(2, 18), 1),
        }

        history = st.session_state.history
        st.session_state.history = pd.concat(
            [history, pd.DataFrame([row])],
            ignore_index=True
        ).tail(MAX_HISTORY)

        st.session_state.last_received_at = stamp
        st.session_state.api_error = None

    except requests.exceptions.RequestException:
        st.session_state.api_error = (
            f"Cannot connect to Flask at {API_URL}. "
            "Make sure api.py is running."
        )
    except (ValueError, TypeError) as error:
        st.session_state.api_error = str(error)


def style_chart(fig, height=320):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#526a80", size=11),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#dbe7f0")
    fig.update_yaxes(gridcolor="#edf2f7")
    return fig


def render_dashboard():
    initialize_state()
    fetch_sensor_data()

    df = st.session_state.history.copy()

    st.markdown("""
    <div class="hero">
        <div class="hero-title">🌿 EcoTwin</div>
        <div class="hero-subtitle">
            Smart Environment Dashboard · ESP32 readings via Flask
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.api_error:
        st.error(st.session_state.api_error)
    elif df.empty:
        st.info(
            "Waiting for the first sensor reading. Keep api.py running "
            "and check that your ESP32 is posting data to Flask."
        )
    else:
        st.success("Flask connected · Sensor readings received")

    if df.empty:
        st.markdown("""
        <div class="panel">
            <div class="panel-title">Your dashboard</div>
            Actual soil moisture and light values will appear here.
            Temperature and wind will use mock demonstration values.
        </div>
        """, unsafe_allow_html=True)
        return

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else None

    st.subheader("Current conditions")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🌱 Soil Moisture",
        f'{latest["Soil Moisture"]:.0f}%',
        delta=(
            f'{latest["Soil Moisture"] - previous["Soil Moisture"]:+.0f} pp'
            if previous is not None else None
        ),
        help="Actual reading from your YL-69 sensor."
    )

    col2.metric(
        "☀️ Light Level",
        f'{latest["Light"]:.0f}%',
        delta=(
            f'{latest["Light"] - previous["Light"]:+.0f} pp'
            if previous is not None else None
        ),
        help="Actual reading from your LDR module."
    )

    col3.metric(
        "🌡️ Temperature",
        f'{latest["Temperature"]:.1f} °C',
        help="Mock value. No temperature sensor is connected."
    )

    col4.metric(
        "💨 Wind Speed",
        f'{latest["Wind Speed"]:.1f} km/h',
        help="Mock value. No wind sensor is connected."
    )

    st.caption(
        "Soil moisture and light are real sensor readings. "
        "Temperature and wind are simulated, not actual measurements."
    )

    left, right = st.columns([1.6, 1])

    with left:
        st.markdown(
            '<div class="panel"><div class="panel-title">'
            'Soil moisture and light trends</div>',
            unsafe_allow_html=True
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Soil Moisture"],
            name="Soil Moisture",
            mode="lines+markers",
            line=dict(color="#16a34a", width=2.5),
            marker=dict(size=5),
        ))
        fig.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Light"],
            name="Light",
            mode="lines+markers",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=5),
        ))
        fig.update_yaxes(title="Percentage (%)", range=[0, 100])
        st.plotly_chart(
            style_chart(fig), use_container_width=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="panel"><div class="panel-title">'
            'Environment overview</div>',
            unsafe_allow_html=True
        )

        score = round(
            (latest["Soil Moisture"] + latest["Light"]) / 2
        )

        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={
                "suffix": "/100",
                "font": {"color": "#17324d", "size": 32}
            },
            title={
                "text": "Combined sensor score",
                "font": {"color": "#526a80", "size": 14}
            },
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#16a34a"},
                "bgcolor": "#f8fbfd",
                "bordercolor": "#dbe7f0",
                "steps": [
                    {"range": [0, 35], "color": "#fee2e2"},
                    {"range": [35, 70], "color": "#dbeafe"},
                    {"range": [70, 100], "color": "#dcfce7"},
                ],
            },
        ))

        st.plotly_chart(
            style_chart(gauge, 245), use_container_width=True
        )
        st.caption(
            "A simple average of the two sensor percentages, "
            "not a scientific plant-health diagnosis."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Simple recommendations")
    rec1, rec2 = st.columns(2)

    with rec1:
        if latest["Soil Moisture"] < 35:
            st.warning(
                "🌱 Soil moisture is low. Check whether watering is needed."
            )
        elif latest["Soil Moisture"] > 80:
            st.info(
                "💧 Soil moisture is high. Check that the soil "
                "is not staying too wet."
            )
        else:
            st.success(
                "🌱 Soil moisture is within this dashboard's example range."
            )

    with rec2:
        if latest["Light"] < 25:
            st.warning(
                "☀️ Light is low. Consider a brighter location if suitable."
            )
        elif latest["Light"] > 85:
            st.info(
                "🌤️ Light is high. Check whether your plant needs shade."
            )
        else:
            st.success(
                "☀️ Light is within this dashboard's example range."
            )

    st.caption(
        "Thresholds are examples. Calibrate your sensors and adjust "
        "the thresholds for your plant."
    )

    st.subheader("Recent readings")
    recent = df.tail(12).iloc[::-1].copy()
    recent["Time"] = pd.to_datetime(
        recent["Time"]
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    recent = recent.rename(columns={
        "Time": "Received time",
        "Soil Moisture": "Soil Moisture (%)",
        "Light": "Light (%)",
        "Temperature": "Mock Temperature (°C)",
        "Wind Speed": "Mock Wind (km/h)",
    })

    st.dataframe(
        recent, use_container_width=True, hide_index=True
    )

    st.download_button(
        "Download reading history (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="ecotwin_readings.csv",
        mime="text/csv",
    )

    st.caption(
        f"Updated {datetime.now().strftime('%H:%M:%S')} · "
        f"{len(df)} readings stored temporarily in this session."
    )


initialize_state()

# Refresh the single page every five seconds.
if hasattr(st, "fragment"):
    @st.fragment(run_every=POLL_SECONDS)
    def live_dashboard():
        render_dashboard()

    live_dashboard()
else:
    render_dashboard()
    st.warning(
        "Automatic refresh requires a newer Streamlit version. "
        "Upgrade with: python -m pip install --upgrade streamlit"
    )
