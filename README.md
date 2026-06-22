# INF8808E Project — Montréal Cycling Dashboard

A Python + Plotly/Dash dashboard for **Evidence-Based Insights for Montréal's Cycling Network**.

The dashboard uses Montréal's network of permanent cyclist counters to move the city's
cycling debate from opinion toward evidence. It is built as a decision-support tool for
urban planners and is organized around three questions: **Where** people cycle, **When**
they cycle, and **What** corridors to prioritize for investment.

## Visualizations

The dashboard is a three-tab layout:

- **Where?** — Borough choropleth of mean daily volume per counter, with a toggleable
  counting-site bubble overlay.
- **When?** — An hour-by-day heatmap filterable by season and borough, and a
  diverging bar chart of directional peak-hour flow per corridor.
- **What?** — A corridor-prioritization scatter plot with interactive volume and
  winter-retention thresholds.

## Data Source

Official dataset page:

https://donnees.montreal.ca/dataset/cyclistes

Dataset title: `Compteurs cyclistes permanents`
Raw data filename: Cyclistes CSV

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Running the Dashboard

Precomputed data is already committed to the repository, so the dashboard runs out of the
box. Start it with:

```bash
python server.py
```

Default local URL:

```text
http://127.0.0.1:8050/
```

## Preprocessing (only needed to refresh the data)

The dashboard reads precomputed CSVs that are already included in `data/`. You only
need to run preprocessing if you want to regenerate them from updated source data.

To do so, download the raw dataset and place it in the `data/` folder, then run:

```bash
python build_data.py
```

This reads the raw records and writes the precomputed files the dashboard loads at startup


## Folder Structure

```text
.
├── server.py            # entry point (failsafe wrapper)
├── app.py               # single Dash app
├── build_data.py        # offline preprocessing: raw data -> precomputed CSVs
├── load_data.py         # loaders for the precomputed CSVs
├── const.py             # shared constants and file paths
├── visualizations/
│   ├── map.py           # choropleth + bubble overlay
│   ├── heatmap.py       # hour × day heatmap
│   ├── diverging.py     # directional peak-hour flow
│   └── scatter.py       # corridor prioritization scatter
└── data/                # precomputed CSVs (committed); raw data (gitignored)
```