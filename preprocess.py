from pathlib import Path

import pandas as pd
import requests


DATASET_PAGE_URL = "https://donnees.montreal.ca/dataset/cyclistes"
RESOURCE_ID = "a8e463ab-d334-4714-81d5-8da0310d80c0"

RAW_DATA_PATH = Path("cyclistes.csv")
VIZ2_OUTPUT_PATH = Path("heatmap_viz2.csv")
API_HEADERS = {"User-Agent": "Mozilla/5.0"}
LOCAL_TIMEZONE = "America/Montreal"

REQUIRED_COLUMNS = {"agg_code", "instance", "arrondissement", "periode", "volume"}

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
}

SEASON_ORDER = {
    "All year": 0,
    "Winter": 1,
    "Spring": 2,
    "Summer": 3,
    "Fall": 4,
}

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ORDER_MAP = {day: index for index, day in enumerate(DAY_ORDER)}


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


def load_raw_data(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Loads local data, or downloads hourly data when the local file is missing/invalid."""
    if not path.exists():
        print(f"{path} not found. Downloading hourly data from {DATASET_PAGE_URL}...")
        return download_hourly_data(path)

    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        print(
            f"{path} is not the expected cyclist CSV; missing columns: {sorted(missing)}."
        )
        print("Downloading hourly data from the official Montreal API instead...")
        return download_hourly_data(path)

    return df



def prepare_viz2_hourly_data(df_hourly: pd.DataFrame) -> pd.DataFrame:
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


def _mean_volume_by_group(site_hourly: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (
        site_hourly
        .groupby(group_cols, as_index=False)
        .agg(
            mean_volume=("volume", "mean"),
            sample_size=("volume", "size"),
        )
    )


def build_viz2_heatmap_data(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the hour x day heatmap dataset for Visualization 2.

    Metric: mean hourly cyclist volume per counter.
    Lanes and directions are summed first at counter-hour level, then averaged
    by borough, season, day, and hour.
    """
    df = prepare_viz2_hourly_data(df_hourly)

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
        .reset_index(drop=True)
    )


def main() -> None:
    raw_data = load_raw_data()
    viz2_heatmap = build_viz2_heatmap_data(raw_data)
    viz2_heatmap.to_csv(VIZ2_OUTPUT_PATH, index=False)
    print(f"Wrote {len(viz2_heatmap)} rows to {VIZ2_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
