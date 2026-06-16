from pathlib import Path


DATASET_PAGE_URL = "https://donnees.montreal.ca/dataset/cyclistes"
RESOURCE_ID = "a8e463ab-d334-4714-81d5-8da0310d80c0"
BOROUGH_GEOJSON_URL = (
    "https://donnees.montreal.ca/dataset/9797a946-9da8-41ec-8815-f6b276dec7e9/"
    "resource/e18bfd07-edc8-4ce8-8a5a-3b617662a794/download/"
    "limites-administratives-agglomeration.geojson"
)


RAW_DATA_PATH = Path("data/cyclistes.csv")
API_HEADERS = {"User-Agent": "Mozilla/5.0"}
LOCAL_TIMEZONE = "America/Montreal"


REQUIRED_COLUMNS = {
    "agg_code",
    "instance",
    "longitude",
    "latitude",
    "arrondissement",
    "rue_1",
    "rue_2",
    "periode",
    "volume",
}


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

HOUR_ORDER = list(range(24))
HOUR_LABELS = [f"{hour:02d}:00" for hour in HOUR_ORDER]


HOURLY_PATH = Path("data/hourly_data.csv")
MONTHLY_PATH = Path("data/monthly_data.csv")


HEATMAP_DATA_PATH = Path("data/heatmap_viz2.csv")
SCATTER_DATA_PATH = Path("data/scatter_viz4.csv")
MAP_DATA_PATH = Path("data/map_viz1.csv")
GEOJSON_PATH = Path("data/montreal_boroughs.geojson")