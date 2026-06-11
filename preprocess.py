import pandas as pd

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall",   10: "Fall",  11: "Fall"
}

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

df_raw = pd.read_csv("cyclistes.csv")

BOROUGH = df_raw['arrondissement'].unique()

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


agg_dfs = split_by_agg(df_raw)