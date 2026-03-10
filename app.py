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
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Lexend', sans-serif;
}

.stApp {
    background-color: #f8fbff;
}

.main-title {
    font-size: 34px;
    font-weight: 700;
    color: #1f4e79;
    margin-bottom: 0;
}

.sub-title {
    font-size: 17px;
    color: #4f6f8f;
    margin-top: 0;
    margin-bottom: 20px;
}

.card {
    background-color: white;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-left: 6px solid #f4c542;
}

.section-box {
    background-color: white;
    padding: 16px;
    border-radius: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 18px;
}

div[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #e6eef7;
    padding: 14px;
    border-radius: 14px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}

h2, h3 {
    color: #1f4e79;
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
st.sidebar.title("Dashboard Filters")

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
    help="Shows only segments with a risk index equal to or above the selected value."
)

filtered_df = df[
    (df["hotspot"].isin(selected_hotspots)) &
    (df["risk_level"].isin(selected_risk_levels)) &
    (df["risk_index"] >= min_risk)
].copy()

# -----------------------------
# Header
# -----------------------------
st.markdown('<p class="main-title">Smart Walkability Monitoring System</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Sidewalk Risk Prioritization Dashboard for LGU Monitoring</p>', unsafe_allow_html=True)

st.markdown("""
<div class="card">
This dashboard helps identify sidewalk segments that should be prioritized for maintenance based on hazard frequency,
risk index, and hotspot analysis. It is intended to support LGU decision-making for safer and more walkable streets.
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
st.subheader("2D Sidewalk Risk Map")

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
            return "#ff1f1f"   # bright red
        elif risk_level == "Medium Risk":
            return "#ff7a7a"   # medium red
        else:
            return "#ffd6d6"   # light red

    for _, row in filtered_df.iterrows():
        popup_html = f"""
        <div style="font-family: Lexend, sans-serif; font-size: 13px;">
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
            radius=5,  # fixed smaller marker size
            color=get_risk_color(row["risk_level"]),
            fill=True,
            fill_color=get_risk_color(row["risk_level"]),
            fill_opacity=0.8,
            weight=1,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    st_folium(m, width=None, height=520, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Priority Table Section
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("Priority Repair List")

priority_df = filtered_df.sort_values(
    by=["risk_index", "total_hazards"],
    ascending=[False, False]
)[["segment_id", "risk_index", "total_hazards", "risk_level", "priority"]]

priority_df.columns = ["Segment ID", "Risk Index", "Total Hazards", "Risk Level", "Priority"]

st.dataframe(priority_df, use_container_width=True, height=320)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Charts Section
# -----------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.subheader("Hazard Distribution")

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
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Lexend", size=12),
        showlegend=False
    )
    st.plotly_chart(fig_hazards, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.subheader("Risk Distribution Across Segments")

    fig_risk = px.histogram(
        filtered_df,
        x="risk_index",
        nbins=12,
        color_discrete_sequence=["#5b8def"]
    )
    fig_risk.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Lexend", size=12)
    )
    st.plotly_chart(fig_risk, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Download Section
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("Export Filtered Data")

csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Filtered CSV",
    data=csv,
    file_name="filtered_sidewalk_risk_data.csv",
    mime="text/csv"
)
st.markdown('</div>', unsafe_allow_html=True)
