import json

import pandas as pd
import requests



from const import *


def load_scatter_data():
    if not SCATTER_DATA_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(SCATTER_DATA_PATH)
    return df


def load_heatmap_data() -> pd.DataFrame:
    if not HEATMAP_DATA_PATH.exists():
        return pd.DataFrame()

    data = pd.read_csv(HEATMAP_DATA_PATH)
    data = data.dropna(subset=["arrondissement", "season", "day", "hour", "mean_volume"])
    data["hour"] = pd.to_numeric(data["hour"], errors="coerce")
    data["mean_volume"] = pd.to_numeric(data["mean_volume"], errors="coerce")
    data = data.dropna(subset=["hour", "mean_volume"])
    data["hour"] = data["hour"].astype(int)
    return data

def load_map_data() -> pd.DataFrame:
    if not MAP_DATA_PATH.exists():
        return pd.DataFrame()

    data = pd.read_csv(MAP_DATA_PATH)

    numeric_cols = ["mean_daily_volume", "total_volume", "active_days", "longitude", "latitude"]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    required_cols = [
        "instance",
        "arrondissement",
        "rue_1",
        "rue_2",
        "longitude",
        "latitude",
        "mean_daily_volume",
    ]

    data = data.dropna(subset=required_cols)

    return data

def load_borough_geojson() -> dict:
    if not GEOJSON_PATH.exists():
        response = requests.get(BOROUGH_GEOJSON_URL, timeout=60)
        response.raise_for_status()
        GEOJSON_PATH.write_text(response.text, encoding="utf-8")

    return json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))