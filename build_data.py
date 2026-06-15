from pathlib import Path

import pandas as pd
import requests

from const import (
    API_HEADERS,
    RAW_DATA_PATH,
    RESOURCE_ID,
    DAY_ORDER_MAP,
    SEASON_ORDER,
    MONTHLY_PATH,
    HOURLY_PATH,
    HEATMAP_DATA_PATH,
    SCATTER_DATA_PATH,
    LOCAL_TIMEZONE,
    SEASON_MAP,
    DAY_ORDER,
)


#######################################
#### FOR DATA PREP FOR EACHH VIE W#####
#######################################

######################################
###### GLOBAL FUNCTIONS ##############
######################################



def download_hourly_data(output_path: Path = RAW_DATA_PATH, batch_size: int = 5000) -> pd.DataFrame:
    """Downloads only hourly records from the official Montreal CKAN API.

    The direct CSV URL can return RBAC errors, and offset pagination can be
    blocked on large offsets. This uses SQL keyset pagination with _id instead.
    """
    import time

    all_records = []
    last_id = 0
    downloaded = 0

    count_sql = f"SELECT count(*) as n FROM \"{RESOURCE_ID}\" WHERE agg_code = 'h'"
    count_response = requests.get(
        "https://donnees.montreal.ca/api/3/action/datastore_search_sql",
        params={"sql": count_sql},
        headers=API_HEADERS,
        timeout=60,
    )
    count_response.raise_for_status()
    total = int(count_response.json()["result"]["records"][0]["n"])

    fields = [
        "_id",
        "agg_code",
        "instance",
        "arrondissement",
        "periode",
        "volume",
    ]
    field_sql = ", ".join(fields)

    while True:
        sql = (
            f'SELECT {field_sql} FROM "{RESOURCE_ID}" '
            f"WHERE agg_code = 'h' AND _id > {last_id} "
            f"ORDER BY _id LIMIT {batch_size}"
        )

        for attempt in range(5):
            try:
                response = requests.get(
                    "https://donnees.montreal.ca/api/3/action/datastore_search_sql",
                    params={"sql": sql},
                    headers=API_HEADERS,
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException:
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))

        if not payload.get("success"):
            raise RuntimeError(f"Montreal API request failed: {payload}")

        records = payload["result"]["records"]
        if not records:
            break

        all_records.extend(records)
        last_id = max(int(record["_id"]) for record in records)
        downloaded += len(records)
        print(f"Downloaded {downloaded:,} / {total:,} hourly rows")

        if len(records) < batch_size:
            break

        time.sleep(0.1)

    df = pd.DataFrame(all_records)
    df.to_csv(output_path, index=False)
    return df

def split_by_agg(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Splits the raw dataframe into separate dataframes per aggregation level.
    Each sub-dataframe is self-consistent and can be used independently.
    
    Returns a dict with keys: 'f' (15min), 'h' (hourly), 'd' (daily), 
                                'm' (monthly), 'y' (yearly)
    """
    df["periode"] = pd.to_datetime(df["periode"], utc=True).dt.tz_convert("America/Montreal")
    
    agg_dfs = {}
    for code in ["f", "h", "d", "m", "y"]:
        agg_dfs[code] = df[df["agg_code"] == code].copy().reset_index(drop=True)
    
    return agg_dfs



def _mean_volume_by_group(site_hourly: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (
        site_hourly
        .groupby(group_cols, as_index=False)
        .agg(
            mean_volume=("volume", "mean"),
            sample_size=("volume", "size"),
        )
    )


#######################################################
############# Functions for vis 2 data prep #############
########################################################

def prepare_heatmap_hourly_data(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans hourly cyclist counter data for Visualization 2.

    Visualization 2 must use only hourly records. If a larger dataframe is
    passed, this function still enforces agg_code == "h".
    """
    df = df_hourly.copy()

    if "agg_code" in df.columns:
        df = df[df["agg_code"] == "h"].copy()

    df["periode"] = pd.to_datetime(df["periode"], utc=True, errors="coerce")
    df["periode"] = df["periode"].dt.tz_convert(LOCAL_TIMEZONE)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df["arrondissement"] = df["arrondissement"].astype("string").str.strip()
    df["instance"] = df["instance"].astype("string").str.strip()

    df = df.dropna(subset=["periode", "volume", "arrondissement", "instance"])
    df = df[
        (df["volume"] >= 0)
        & (df["arrondissement"] != "")
        & (df["instance"] != "")
    ].copy()

    df["hour"] = df["periode"].dt.hour
    df["day_order"] = df["periode"].dt.dayofweek
    df["day"] = df["day_order"].map(dict(enumerate(DAY_ORDER)))
    df["season"] = df["periode"].dt.month.map(SEASON_MAP)

    return df


def build_heatmap_dataset(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the hour x day heatmap dataset for Visualization 2.

    Metric: mean hourly cyclist volume per counter.
    Lanes and directions are summed first at counter-hour level, then averaged
    by borough, season, day, and hour.
    """
    df = prepare_heatmap_hourly_data(df_hourly)

    output_cols = [
        "arrondissement",
        "season",
        "day",
        "hour",
        "mean_volume",
        "sample_size",
        "day_order",
        "season_order",
    ]

    if df.empty:
        return pd.DataFrame(columns=output_cols)

    site_hourly = (
        df
        .groupby(
            ["instance", "arrondissement", "periode", "hour", "day", "season"],
            as_index=False,
        )["volume"]
        .sum()
    )

    borough_heatmap = _mean_volume_by_group(
        site_hourly,
        ["arrondissement", "season", "day", "hour"],
    )

    all_montreal = _mean_volume_by_group(
        site_hourly,
        ["season", "day", "hour"],
    )
    all_montreal["arrondissement"] = "All Montréal"

    borough_all_year = _mean_volume_by_group(
        site_hourly,
        ["arrondissement", "day", "hour"],
    )
    borough_all_year["season"] = "All year"

    all_montreal_all_year = _mean_volume_by_group(
        site_hourly,
        ["day", "hour"],
    )
    all_montreal_all_year["arrondissement"] = "All Montréal"
    all_montreal_all_year["season"] = "All year"

    heatmap_data = pd.concat(
        [
            borough_heatmap,
            all_montreal,
            borough_all_year,
            all_montreal_all_year,
        ],
        ignore_index=True,
    )

    heatmap_data["day_order"] = heatmap_data["day"].map(DAY_ORDER_MAP)
    heatmap_data["season_order"] = heatmap_data["season"].map(SEASON_ORDER)
    heatmap_data["mean_volume"] = heatmap_data["mean_volume"].round(3)

    return (
        heatmap_data[output_cols]
        .sort_values(["season_order", "arrondissement", "day_order", "hour"])
        .reset_index(drop=True))



#############################################################
################### Function for vis 4 data prep ############
#############################################################


def prepare_scatter_data(df_monthly: pd.DataFrame,
                         df_hourly: pd.DataFrame,
                         season: str = "Summer") -> pd.DataFrame:
    df_monthly = df_monthly.copy()
    df_monthly["periode"] = (
        pd.to_datetime(df_monthly["periode"], utc=True)
        .dt.tz_convert("America/Montreal")
    )
    df_monthly["month"] = df_monthly["periode"].dt.month
    df_monthly["season"] = df_monthly["month"].map(SEASON_MAP)
    df_monthly["corridor"] = df_monthly["rue_1"] + " & " + df_monthly["rue_2"]

    # Seasonal mean volume per corridor
    seasonal = (
        df_monthly.groupby(["corridor", "arrondissement", "season"])["volume"]
        .mean().reset_index()
    )
    # summer = seasonal[~(seasonal["season"] == season)].set_index("corridor")["volume"]
    winter = seasonal[seasonal["season"] == "Winter"].set_index("corridor")["volume"]

    # (Spring + Summer + Fall), not summer alone.
    summer = (
        df_monthly[df_monthly["season"] != "Winter"]
        .groupby("corridor")["volume"].mean()
    )  

    per_counter = (
    df_monthly
    .groupby(["corridor", "arrondissement", "instance", "periode"], as_index=False)["volume"]
    .sum()
)

    # total = (
    #     df_monthly.groupby("corridor")["volume"].mean()
    #     .reset_index().rename(columns={"volume": "mean_volume"})
    # )

    total = (
    per_counter.groupby("corridor")["volume"].mean()
    .reset_index().rename(columns={"volume": "mean_volume"})
    )


    borough = (
        df_monthly.groupby("corridor")["arrondissement"].first().reset_index()
    )
    n_sensors = (
        df_monthly.groupby("corridor")["instance"].nunique()
        .reset_index().rename(columns={"instance": "n_sensors"})
    )

    # Peak hour volume per corridor (AM 7-9h + PM 16-18h)
    df_hourly = df_hourly.copy()
    df_hourly["periode"] = (
        pd.to_datetime(df_hourly["periode"], utc=True)
        .dt.tz_convert("America/Montreal")
    )
    df_hourly["hour"] = df_hourly["periode"].dt.hour
    df_hourly["corridor"] = df_hourly["rue_1"] + " & " + df_hourly["rue_2"]
    peak = (
        df_hourly[df_hourly["hour"].between(7, 9) |
                  df_hourly["hour"].between(16, 18)]
        .groupby("corridor")["volume"].mean()
        .reset_index().rename(columns={"volume": "peak_volume"})
    )

    scatter_df = total.merge(borough, on="corridor")
    scatter_df = scatter_df.merge(n_sensors, on="corridor")
    scatter_df = scatter_df.merge(peak, on="corridor", how="left")

    # scatter_df["volume_per_sensor"] = (
    #     scatter_df["mean_volume"] / scatter_df["n_sensors"]
    # )
    scatter_df["winter_retention"] = (
        winter.reindex(scatter_df["corridor"].values).values /
        summer.reindex(scatter_df["corridor"].values).values
    )

    scatter_df = scatter_df.dropna(subset=["winter_retention"])
    scatter_df = scatter_df[scatter_df["winter_retention"] != float("inf")]
    return scatter_df

def load_scatter_df(season: str = "Summer") -> pd.DataFrame:
    df_monthly = pd.read_csv(MONTHLY_PATH)
    df_hourly = pd.read_csv(HOURLY_PATH)
    return prepare_scatter_data(df_monthly, df_hourly, season=season)

if __name__ == "__main__":
    # print("Downloading hourly data from Montreal CKAN API...")
    # df_hourly = download_hourly_data()
    print("Loading raw data from local CSV...")
    df_raw = pd.read_csv(RAW_DATA_PATH)
    aggs = split_by_agg(df_raw)
    aggs["h"].to_csv(HOURLY_PATH, index=False)
    aggs["m"].to_csv(MONTHLY_PATH, index=False)
    print(f"Hourly data saved to {HOURLY_PATH}")
    print(f"Monthly data saved to {MONTHLY_PATH}")

    print("Building heatmap dataset...")
    heatmap_df = build_heatmap_dataset(aggs["h"])
    heatmap_df.to_csv(HEATMAP_DATA_PATH, index=False)
    print(f"Heatmap dataset saved to {HEATMAP_DATA_PATH}")

    print("Preparing scatter dataset...")
    scatter_df = load_scatter_df()
    scatter_df.to_csv(SCATTER_DATA_PATH, index=False)
    print(f"Scatter dataset saved to {SCATTER_DATA_PATH}")
