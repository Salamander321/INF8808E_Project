import pandas as pd
import plotly.graph_objects as go



def find_borough_name_property(geojson: dict) -> str:
    if not geojson.get("features"):
        raise ValueError("GeoJSON has no features.")

    properties = geojson["features"][0].get("properties", {})
    possible_names = [
        "NOM",
        "nom",
        "NOM_ARROND",
        "NOM_ARRONDISSEMENT",
        "arrondissement",
        "ARRONDISSEMENT",
    ]

    for name in possible_names:
        if name in properties:
            return name

    raise ValueError(f"Could not find borough name property. Available properties: {list(properties.keys())}")


def make_empty_map_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": "#5f6b7a"},
        align="center",
    )
    fig.update_layout(
        height=650,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    return fig


def build_borough_summary(map_data: pd.DataFrame) -> pd.DataFrame:
    borough_summary = (
        map_data
        .groupby("arrondissement", as_index=False)
        .agg(
            mean_daily_volume=("mean_daily_volume", "mean"),
            n_counters=("instance", "nunique"),
            total_volume=("total_volume", "sum"),
        )
    )

    borough_summary["mean_daily_volume"] = borough_summary["mean_daily_volume"].round(1)
    borough_summary["total_volume"] = borough_summary["total_volume"].round(0)

    return borough_summary


def get_figure(map_data: pd.DataFrame, geojson: dict, show_bubbles: bool) -> go.Figure:

    if map_data.empty:
        return make_empty_map_figure(
            "Run python preprocess.py first to generate map_viz1.csv."
        )
    
    borough_property = find_borough_name_property(geojson)
    borough_summary = build_borough_summary(map_data)

    fig = go.Figure()

    fig.add_trace(
        go.Choroplethmapbox(
            geojson=geojson,
            locations=borough_summary["arrondissement"],
            z=borough_summary["mean_daily_volume"],
            featureidkey=f"properties.{borough_property}",
            colorscale="Blues",
            marker_opacity=0.95,
            marker_line_width=0.8,
            marker_line_color="white",
            colorbar={
                "title": "Mean daily<br>volume",
            },
            customdata=borough_summary[["n_counters", "total_volume"]],
            hovertemplate=(
                "<b>%{location}</b><br>"
                "Mean daily volume per counter: %{z:.1f}<br>"
                "Number of counters: %{customdata[0]}<br>"
                "Total volume: %{customdata[1]:.0f}"
                "<extra></extra>"
            ),
            name="Borough volume",
        )
    )

    if show_bubbles:
        bubble_data = map_data.copy()

        max_volume = bubble_data["mean_daily_volume"].max()
        if max_volume > 0:
            bubble_sizes = 8 + 32 * (bubble_data["mean_daily_volume"] / max_volume)
        else:
            bubble_sizes = 10

        bubble_data["corridor"] = (
            bubble_data["rue_1"].astype(str)
            + " / "
            + bubble_data["rue_2"].astype(str)
        )

        fig.add_trace(
            go.Scattermapbox(
                lat=bubble_data["latitude"],
                lon=bubble_data["longitude"],
                mode="markers",
                marker={
                    "size": bubble_sizes,
                    "opacity": 0.68,
                    "color": bubble_data["mean_daily_volume"],
                    "colorscale": "Blues",
                    "showscale": False,
                },
                customdata=bubble_data[
                    ["corridor", "arrondissement", "mean_daily_volume", "active_days"]
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Borough: %{customdata[1]}<br>"
                    "Mean daily volume: %{customdata[2]:.1f}<br>"
                    "Active days: %{customdata[3]}"
                    "<extra></extra>"
                ),
                name="Counting sites",
            )
        )

    fig.update_layout(
        title={
            "text": "Borough volume with counting-site overlay",
            "x": 0,
            "xanchor": "left",
        },
        mapbox={
            "style": "carto-positron",
            "center": {"lat": 45.541, "lon": -73.65},
            "zoom": 9.75,
        },
        height=650,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        paper_bgcolor="#ffffff",
        font={"color": "#1f2933"},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 0.01,
            "xanchor": "left",
            "x": 0.01,
        },
    )

    return fig