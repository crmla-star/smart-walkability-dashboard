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
# Load data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("segment_gi_star.csv")

    # Clean text columns
    df["hotspot"] = df["hotspot"].fillna("Not Significant").astype(str)
    df["damage"] = df["damage"].fillna("Intact").astype(str)

    # Risk level classification
    def classify_risk(x):
        if x >= 6:
            return "High Risk"
        elif x >= 3:
            return "Medium Risk"
        else:
            return "Low Risk"

    df["risk_level"] = df["risk_index"].apply(classify_risk)

    # Priority classification
    def classify_priority(x):
        if x >= 6:
            return "Immediate Repair"
        elif x >= 3:
            return "Monitor"
        else:
            return "Low Priority"

    df["priority"] = df["risk_index"].apply(classify_priority)

    return df

df = load_data()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Filters")

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
    value=float(df["risk_index"].min())
)

# Filtered dataframe
filtered_df = df[
    (df["hotspot"].isin(selected_hotspots)) &
    (df["risk_level"].isin(selected_risk_levels)) &
    (df["risk_index"] >= min_risk)
].copy()

# -----------------------------
# Title
# -----------------------------
st.title("Smart Walkability Monitoring System")
st.markdown("### Sidewalk Risk Prioritization Dashboard for LGU Monitoring")

st.markdown(
    """
    This dashboard helps identify sidewalk segments that should be prioritized
    for maintenance based on hazard frequency, risk index, and hotspot analysis.
    """
)

# -----------------------------
# KPI Cards
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Segments", f"{len(filtered_df)}")
k2.metric("Total Hazards", f"{int(filtered_df['total_hazards'].sum())}")
k3.metric("Average Risk Index", f"{filtered_df['risk_index'].mean():.2f}")
k4.metric(
    "Hotspot Segments",
    f"{int((filtered_df['hotspot'].str.lower() == 'hotspot').sum())}"
)

st.divider()

# -----------------------------
# Map + Priority Table
# -----------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader("2D Sidewalk Risk Map")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
    else:
        center_lat = filtered_df["lat"].mean()
        center_long = filtered_df["long"].mean()

        m = folium.Map(
            location=[center_lat, center_long],
            zoom_start=17,
            tiles="OpenStreetMap"
        )

        def get_color(hotspot_value):
            hv = str(hotspot_value).strip().lower()
            if hv == "hotspot":
                return "red"
            elif hv == "coldspot":
                return "blue"
            else:
                return "gray"

        for _, row in filtered_df.iterrows():
            popup_html = f"""
            <b>Segment ID:</b> {row['segment_id']}<br>
            <b>Risk Index:</b> {row['risk_index']}<br>
            <b>Total Hazards:</b> {row['total_hazards']}<br>
            <b>Damage:</b> {row['damage']}<br>
            <b>Hotspot:</b> {row['hotspot']}<br>
            <b>Risk Level:</b> {row['risk_level']}<br>
            <b>Priority:</b> {row['priority']}
            """

            folium.CircleMarker(
                location=[row["lat"], row["long"]],
                radius=max(5, float(row["risk_index"]) * 1.5),
                color=get_color(row["hotspot"]),
                fill=True,
                fill_color=get_color(row["hotspot"]),
                fill_opacity=0.75,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

        st_folium(m, width=900, height=520)

with right:
    st.subheader("Priority Repair List")

    priority_df = filtered_df.sort_values(
        by=["risk_index", "total_hazards"],
        ascending=[False, False]
    )[["segment_id", "risk_index", "total_hazards", "hotspot", "risk_level", "priority"]]

    st.dataframe(priority_df, use_container_width=True, height=520)

st.divider()

# -----------------------------
# Hazard Distribution
# -----------------------------
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
    title="Detected Sidewalk Hazards by Type"
)

st.plotly_chart(fig_hazards, use_container_width=True)

# -----------------------------
# Risk Distribution
# -----------------------------
st.subheader("Risk Distribution Across Segments")

fig_risk = px.histogram(
    filtered_df,
    x="risk_index",
    nbins=12,
    title="Distribution of Risk Index"
)

st.plotly_chart(fig_risk, use_container_width=True)

# -----------------------------
# Download filtered data
# -----------------------------
st.subheader("Export Filtered Data")

csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Filtered CSV",
    data=csv,
    file_name="filtered_sidewalk_risk_data.csv",
    mime="text/csv"
)
