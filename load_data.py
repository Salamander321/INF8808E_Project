import pandas as pd



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