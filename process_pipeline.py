import os
import time
import warnings
from collections import Counter

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from ultralytics import YOLO
from libpysal.weights import KNN
from esda.moran import Moran
from esda import getisord

# ---------------------------------
# Paths
# ---------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
MODEL_FILE = os.path.join(BASE_DIR, "best.pt")
MAPPING_FILE = os.path.join(BASE_DIR, "mapping_with_coords.csv")

SEGMENT_SUMMARY_CSV = os.path.join(BASE_DIR, "segment_summary.csv")
SEGMENT_GI_STAR_CSV = os.path.join(BASE_DIR, "segment_gi_star.csv")

# Optional debug output
IMAGE_SUMMARY_CSV = os.path.join(BASE_DIR, "image_summary.csv")

# ---------------------------------
# Settings
# ---------------------------------
POLL_SECONDS = 5
CONF_THRESHOLD = 0.25

severity_weights = {
    "surface_crack": 1,
    "narrowed_pathway": 2,
    "major_damage": 3,
    "obstruction": 3,
}

class_map = {
    0: "surface_crack",
    1: "major_damage",
    2: "obstruction",
    3: "narrowed_pathway",
}

# ---------------------------------
# Helpers
# ---------------------------------
def load_model():
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"Model file not found: {MODEL_FILE}")
    return YOLO(MODEL_FILE)


def load_mapping():
    if not os.path.exists(MAPPING_FILE):
        raise FileNotFoundError(f"Mapping file not found: {MAPPING_FILE}")

    mapping = pd.read_csv(MAPPING_FILE)

    required_cols = {"img_name", "segment_id", "lat", "long"}
    missing = required_cols - set(mapping.columns)
    if missing:
        raise ValueError(f"mapping_with_coords.csv is missing columns: {missing}")

    mapping = mapping[["img_name", "segment_id", "lat", "long"]].copy()
    mapping["segment_id"] = pd.to_numeric(mapping["segment_id"], errors="coerce")
    mapping["lat"] = pd.to_numeric(mapping["lat"], errors="coerce")
    mapping["long"] = pd.to_numeric(mapping["long"], errors="coerce")
    mapping = mapping.dropna(subset=["segment_id", "lat", "long"])
    mapping["segment_id"] = mapping["segment_id"].astype(int)

    return mapping


def list_images():
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        return []

    valid_ext = (".png", ".jpg", ".jpeg")
    files = [
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith(valid_ext)
    ]
    return sorted(files)


def build_empty_outputs_from_mapping(mapping):
    segment_summary = mapping.copy()
    segment_summary["surface_crack"] = 0
    segment_summary["major_damage"] = 0
    segment_summary["obstruction"] = 0
    segment_summary["narrowed_pathway"] = 0
    segment_summary["total_hazards"] = 0
    segment_summary["damage"] = "no damage"
    segment_summary["risk_index"] = 0

    segment_summary = segment_summary.sort_values("segment_id").reset_index(drop=True)

    gdf = gpd.GeoDataFrame(
        segment_summary.copy(),
        geometry=gpd.points_from_xy(segment_summary["long"], segment_summary["lat"]),
        crs="EPSG:4326",
    )
    gdf["GiZ"] = np.nan
    gdf["GiP"] = np.nan
    gdf["hotspot"] = "Not significant"

    return segment_summary, gdf


def run_detection(model, image_files):
    image_paths = [os.path.join(IMAGE_FOLDER, img) for img in image_files]

    results = model.predict(
        source=image_paths,
        conf=CONF_THRESHOLD,
        save=False,
        verbose=False
    )

    image_counts = []

    for r in results:
        img_name = os.path.basename(r.path)

        if r.boxes is not None and len(r.boxes.cls) > 0:
            class_ids = r.boxes.cls.tolist()
            hazard_names = [class_map[int(cls)] for cls in class_ids]
            counts = Counter(hazard_names)
        else:
            counts = Counter()

        image_counts.append({
            "img_name": img_name,
            "surface_crack": counts.get("surface_crack", 0),
            "major_damage": counts.get("major_damage", 0),
            "obstruction": counts.get("obstruction", 0),
            "narrowed_pathway": counts.get("narrowed_pathway", 0),
        })

    return pd.DataFrame(image_counts)


def compute_risk(segment_summary):
    segment_summary["total_hazards"] = segment_summary[
        ["surface_crack", "major_damage", "obstruction", "narrowed_pathway"]
    ].sum(axis=1)

    segment_summary["damage"] = np.where(
        segment_summary["total_hazards"] > 0,
        "damage",
        "no damage"
    )

    segment_summary["risk_index"] = (
        segment_summary["surface_crack"] * severity_weights["surface_crack"] +
        segment_summary["narrowed_pathway"] * severity_weights["narrowed_pathway"] +
        segment_summary["major_damage"] * severity_weights["major_damage"] +
        segment_summary["obstruction"] * severity_weights["obstruction"]
    )

    return segment_summary


def compute_hotspots(segment_summary):
    gdf = gpd.GeoDataFrame(
        segment_summary.copy(),
        geometry=[Point(xy) for xy in zip(segment_summary["long"], segment_summary["lat"])],
        crs="EPSG:4326"
    )

    n = len(gdf)
    gdf["GiZ"] = np.nan
    gdf["GiP"] = np.nan
    gdf["hotspot"] = "Not significant"

    if n < 3:
        return gdf

    if gdf["risk_index"].nunique() <= 1:
        return gdf

    k = min(4, max(1, n - 1))

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            coords = list(zip(gdf.geometry.x, gdf.geometry.y))
            knn = KNN.from_array(coords, k=k)
            knn.transform = "r"

            # Moran's I can be computed here if you want to log it
            _ = Moran(gdf["risk_index"], knn)

            gi_star = getisord.G_Local(gdf["risk_index"], knn)
            gdf["GiZ"] = gi_star.Zs
            gdf["GiP"] = gi_star.p_sim

        gdf["hotspot"] = "Not significant"
        gdf.loc[(gdf["GiZ"] > 1.96) & (gdf["GiP"] < 0.05), "hotspot"] = "Hotspot"
        gdf.loc[(gdf["GiZ"] < -1.96) & (gdf["GiP"] < 0.05), "hotspot"] = "Coldspot"

    except Exception as e:
        print(f"[WARN] Hotspot analysis skipped: {e}")

    return gdf


def process_once(model, mapping):
    image_files = list_images()

    if not image_files:
        print("[INFO] No images found. Writing zeroed outputs from mapping.")
        segment_summary, gdf = build_empty_outputs_from_mapping(mapping)
        segment_summary.to_csv(SEGMENT_SUMMARY_CSV, index=False)
        gdf.drop(columns="geometry").to_csv(SEGMENT_GI_STAR_CSV, index=False)
        return

    image_summary = run_detection(model, image_files)
    image_summary = image_summary.merge(mapping, on="img_name", how="left")

    # keep only mapped images
    image_summary = image_summary.dropna(subset=["segment_id", "lat", "long"]).copy()
    image_summary["segment_id"] = image_summary["segment_id"].astype(int)

    image_summary = image_summary[
        [
            "img_name",
            "segment_id",
            "lat",
            "long",
            "surface_crack",
            "major_damage",
            "obstruction",
            "narrowed_pathway",
        ]
    ].sort_values("segment_id").reset_index(drop=True)

    image_summary.to_csv(IMAGE_SUMMARY_CSV, index=False)

    segment_summary = image_summary.groupby("segment_id", as_index=False).agg({
        "img_name": "first",
        "lat": "first",
        "long": "first",
        "surface_crack": "sum",
        "major_damage": "sum",
        "obstruction": "sum",
        "narrowed_pathway": "sum",
    })

    segment_summary = compute_risk(segment_summary)
    segment_summary = segment_summary.sort_values("segment_id").reset_index(drop=True)

    gdf = compute_hotspots(segment_summary)

    segment_summary.to_csv(SEGMENT_SUMMARY_CSV, index=False)
    gdf.drop(columns="geometry").to_csv(SEGMENT_GI_STAR_CSV, index=False)

    print(f"[INFO] Processed {len(image_files)} image(s). CSVs updated.")


def main():
    print("[INFO] Starting backend process pipeline...")
    print(f"[INFO] Watching folder: {IMAGE_FOLDER}")

    model = load_model()
    mapping = load_mapping()

    while True:
        try:
            process_once(model, mapping)
        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
