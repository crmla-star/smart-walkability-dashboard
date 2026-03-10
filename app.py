import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(
    page_title="Smart Walkability Monitoring System",
    layout="wide"
)

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Lexend', sans-serif !important;
    background-color: #f7fafd !important;
    color: #16324f !important;
}

.stApp {
    background: #f7fafd !important;
}

.main-title {
    font-size: 52px;
    font-weight: 800;
    color: #16324f;
    line-height: 1.05;
    margin-bottom: 8px;
}

.sub-title {
    font-size: 22px;
    font-weight: 500;
    color: #4f6b88;
    line-height: 1.3;
    margin-bottom: 0;
}

.card {
    background-color: #ffffff;
    color: #16324f;
    padding: 18px;
    border-radius: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border-left: 6px solid #f4c542;
    font-size: 15px;
}

.section-box {
    background-color: #ffffff;
    color: #16324f;
    padding: 18px;
    border-radius: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 18px;
    border: 1px solid #e7eef6;
}

div[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e7eef6;
    padding: 14px;
    border-radius: 16px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.04);
}

div[data-testid="stMetricLabel"] {
    color: #5a718b !important;
    font-weight: 600;
}

div[data-testid="stMetricValue"] {
    color: #16324f !important;
    font-weight: 800;
}

h1, h2, h3 {
    color: #16324f !important;
    font-family: 'Lexend', sans-serif !important;
}

section[data-testid="stSidebar"] {
    background-color: #eef5fb !important;
    border-right: 1px solid #d9e6f2;
}

section[data-testid="stSidebar"] * {
    color: #16324f !important;
    font-family: 'Lexend', sans-serif !important;
}

section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: #16324f !important;
}

.stSelectbox div, .stMultiSelect div, .stSlider div {
    color: #16324f !important;
}

[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

.stDownloadButton button {
    background-color: #2f80ed !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: 600 !important;
}

.stDownloadButton button:hover {
    background-color: #256fd1 !important;
}

.legend-box {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    margin-top: 8px;
    margin-bottom: 8px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #16324f;
    font-weight: 500;
}

.legend-color {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: inline-block;
    border: 1px solid #d0d7df;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("segment_gi_star.csv")

    df["hotspot"] = df["hotspot"].fillna("Not Significant").astype(str)
    df["damage"] = df["damage"].fillna("Intact").astype(str)

    def classify_risk(x):
        if x >= 6:
            return "High Risk"
        elif x >= 3:
            return "Medium Risk"
        else:
            return "Low Risk"

    def classify_priority(x):
        if x >= 6:
            return "Immediate Repair"
        elif x >= 3:
            return "Monitor"
        else:
            return "Low Priority"

    df["risk_level"] = df["risk_index"].apply(classify_risk)
    df["priority"] = df["risk_index"].apply(classify_priority)

    return df

df = load_data()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown("## Dashboard Filters")

hotspot_options = sorted(df["hotspot"].dropna().unique().tolist())
selected_hotspots = st.sidebar.multiselect(
    "Hotspot Category",
    options=hotspot_options,
    default=hotspot_options
)

risk_options = ["Low Risk", "Medium Risk", "High Risk"]
selected_risk_levels = st.sidebar.multiselect(
    "Risk Level",
    options=risk_options,
    default=risk_options
)

min_risk = st.sidebar.slider(
    "Minimum Risk Index",
    min_value=float(df["risk_index"].min()),
    max_value=float(df["risk_index"].max()),
    value=float(df["risk_index"].min()),
    step=0.5,
    help="Displays only sidewalk segments whose risk index is equal to or higher than the selected threshold."
)

filtered_df = df[
    (df["hotspot"].isin(selected_hotspots)) &
    (df["risk_level"].isin(selected_risk_levels)) &
    (df["risk_index"] >= min_risk)
].copy()

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div style="
    background: linear-gradient(90deg, #ffffff 0%, #f7fbff 100%);
    padding: 22px 28px;
    border-radius: 20px;
    border: 1px solid #e4edf7;
    box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    margin-bottom: 18px;
">
    <div class="main-title">
        Smart Walkability Monitoring System
    </div>
    <div class="sub-title">
        Sidewalk Risk Prioritization Dashboard for LGU Monitoring
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="card">
This dashboard helps identify sidewalk segments that should be prioritized for maintenance based on hazard frequency,
risk index, and hotspot analysis. It supports LGU decision-making by highlighting which sidewalk areas need immediate repair,
monitoring, or lower-priority intervention.
</div>
""", unsafe_allow_html=True)

st.write("")

# -----------------------------
# KPI Cards
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Segments", f"{len(filtered_df)}")
k2.metric("Total Hazards", f"{int(filtered_df['total_hazards'].sum())}")
k3.metric("Average Risk Index", f"{filtered_df['risk_index'].mean():.2f}" if not filtered_df.empty else "0.00")
k4.metric("Hotspot Segments", f"{int((filtered_df['hotspot'].str.lower() == 'hotspot').sum())}")

st.write("")

# -----------------------------
# Map Section
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown("""
<div style="font-size: 24px; font-weight: 700; color: #16324f; margin-bottom: 8px;">
    2D Sidewalk Risk Map
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="legend-box">
    <div class="legend-item"><span class="legend-color" style="background:#9e9e9e;"></span>Low Risk</div>
    <div class="legend-item"><span class="legend-color" style="background:#e57373;"></span>Medium Risk</div>
    <div class="legend-item"><span class="legend-color" style="background:#ff1f1f;"></span>High Risk</div>
</div>
""", unsafe_allow_html=True)

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
else:
    center_lat = filtered_df["lat"].mean()
    center_long = filtered_df["long"].mean()

    m = folium.Map(
        location=[center_lat, center_long],
        zoom_start=17,
        tiles="CartoDB positron"
    )

    def get_risk_color(risk_level):
        if risk_level == "High Risk":
            return "#ff1f1f"
        elif risk_level == "Medium Risk":
            return "#e57373"
        else:
            return "#9e9e9e"

    for _, row in filtered_df.iterrows():
        popup_html = f"""
        <div style="font-family: Lexend, sans-serif; font-size: 13px; color: #16324f;">
            <b>Segment ID:</b> {row['segment_id']}<br>
            <b>Risk Index:</b> {row['risk_index']}<br>
            <b>Total Hazards:</b> {row['total_hazards']}<br>
            <b>Damage:</b> {row['damage']}<br>
            <b>Hotspot:</b> {row['hotspot']}<br>
            <b>Risk Level:</b> {row['risk_level']}<br>
            <b>Priority:</b> {row['priority']}
        </div>
        """

        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=5,
            color=get_risk_color(row["risk_level"]),
            fill=True,
            fill_color=get_risk_color(row["risk_level"]),
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    st_folium(m, width=None, height=540, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Priority Table Section
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown("""
<div style="font-size: 24px; font-weight: 700; color: #16324f; margin-bottom: 10px;">
    Priority Repair List
</div>
""", unsafe_allow_html=True)

priority_df = filtered_df.sort_values(
    by=["risk_index", "total_hazards"],
    ascending=[False, False]
)[["segment_id", "risk_index", "total_hazards", "risk_level", "priority"]].copy()

priority_df.columns = ["Segment ID", "Risk Index", "Total Hazards", "Risk Level", "Priority"]

def priority_color(val):
    if val == "Immediate Repair":
        return "background-color: #ffdddd; color: #8b0000; font-weight: 700;"
    elif val == "Monitor":
        return "background-color: #fff1cc; color: #8a6d00; font-weight: 700;"
    else:
        return "background-color: #eeeeee; color: #4a4a4a; font-weight: 700;"

def risk_gradient(val):
    try:
        if val >= 6:
            return "background-color: #ffcccc; color: #7a0000; font-weight: 700;"
        elif val >= 3:
            return "background-color: #ffe1e1; color: #a33a3a; font-weight: 700;"
        else:
            return "background-color: #f0f0f0; color: #555555; font-weight: 700;"
    except Exception:
        return ""

styled_priority_df = priority_df.style \
    .map(priority_color, subset=["Priority"]) \
    .map(risk_gradient, subset=["Risk Index"])

st.dataframe(styled_priority_df, use_container_width=True, height=340)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Charts Section
# -----------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 24px; font-weight: 700; color: #16324f; margin-bottom: 10px;">
        Hazard Distribution
    </div>
    """, unsafe_allow_html=True)

    hazard_totals = pd.DataFrame({
        "Hazard Type": [
            "Surface Crack",
            "Major Damage",
            "Obstruction",
            "Narrowed Pathway"
        ],
        "Count": [
            filtered_df["surface_crack"].sum(),
            filtered_df["major_damage"].sum(),
            filtered_df["obstruction"].sum(),
            filtered_df["narrowed_pathway"].sum()
        ]
    })

    fig_hazards = px.bar(
        hazard_totals,
        x="Hazard Type",
        y="Count",
        color="Hazard Type",
        color_discrete_sequence=["#f4c542", "#5b8def", "#8ecae6", "#ffd166"]
    )

    fig_hazards.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Lexend", size=12, color="#16324f"),
        showlegend=False,
        title="",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Hazard Type",
        yaxis_title="Count"
    )
    fig_hazards.update_xaxes(tickangle=-25)

    st.plotly_chart(fig_hazards, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 24px; font-weight: 700; color: #16324f; margin-bottom: 10px;">
        Risk Distribution Across Segments
    </div>
    """, unsafe_allow_html=True)

    fig_risk = px.histogram(
        filtered_df,
        x="risk_index",
        nbins=12,
        color_discrete_sequence=["#5b8def"]
    )

    fig_risk.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Lexend", size=12, color="#16324f"),
        title="",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Risk Index",
        yaxis_title="Count"
    )

    st.plotly_chart(fig_risk, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Download Section
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown("""
<div style="font-size: 24px; font-weight: 700; color: #16324f; margin-bottom: 10px;">
    Export Filtered Data
</div>
""", unsafe_allow_html=True)

csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Filtered CSV",
    data=csv,
    file_name="filtered_sidewalk_risk_data.csv",
    mime="text/csv"
)
st.markdown('</div>', unsafe_allow_html=True)
