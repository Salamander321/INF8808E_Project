# INF8808E Project - Montreal Cycling Dashboard

Python + Plotly/Dash dashboard for the project **Evidence-Based Insights for Montreal's Cycling Network**.

The current implementation focuses on Visualization 2: an hour-by-day heatmap of cyclist activity by season and borough.

## Data Source

Official dataset page:

https://donnees.montreal.ca/dataset/cyclistes

Dataset title: `Compteurs cyclistes permanents`

The direct CSV download can return `RBAC: access denied`. The preprocessing script therefore retrieves hourly records through the official CKAN API.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Preprocessing

```bash
python preprocess.py
```

This creates the generated data file used by the dashboard:

```text
heatmap_viz2.csv
```

The raw file `cyclistes.csv` and the processed file `heatmap_viz2.csv` are generated locally and ignored by Git.

## Dashboard

```bash
python app.py
```

Default local URL:

```text
http://127.0.0.1:8050/
```

## Visualization 2 Metric

The heatmap uses hourly records only: `agg_code == "h"`.

Metric:

```text
Mean hourly cyclist volume per counter
```

Preprocessing first sums lanes and directions at the same counter-hour level, then computes averages by borough, season, day, and hour. This keeps borough comparisons from being driven only by the number of counters available in each borough.
