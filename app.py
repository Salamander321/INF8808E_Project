import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from viz.viz1_map import make_viz1_figure

HEATMAP_DATA_PATH = Path("heatmap_viz2.csv")

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOUR_ORDER = list(range(24))
HOUR_LABELS = [f"{hour:02d}:00" for hour in HOUR_ORDER]
SEASON_ORDER = ["All year", "Winter", "Spring", "Summer", "Fall"]

PAGE_STYLE = {
    "maxWidth": "1180px",
    "margin": "32px auto",
    "padding": "0 20px",
    "fontFamily": "Inter, Arial, sans-serif",
    "color": "#1f2933",
}

CARD_STYLE = {
    "background": "#ffffff",
    "border": "1px solid #d8dee7",
    "borderRadius": "8px",
    "padding": "24px",
    "boxShadow": "0 1px 2px rgba(15, 23, 42, 0.06)",
}

CONTROL_ROW_STYLE = {
    "display": "flex",
    "gap": "16px",
    "flexWrap": "wrap",
    "alignItems": "end",
    "margin": "18px 0",
}

CONTROL_STYLE = {
    "display": "grid",
    "gap": "6px",
    "minWidth": "240px",
}

NOTE_STYLE = {
    "color": "#5f6b7a",
    "fontSize": "14px",
    "lineHeight": "1.5",
}


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


def get_borough_options(data: pd.DataFrame) -> list[dict[str, str]]:
    if data.empty:
        return [{"label": "All Montréal", "value": "All Montréal"}]

    boroughs = sorted(data["arrondissement"].dropna().unique())
    ordered = ["All Montréal"] + [borough for borough in boroughs if borough != "All Montréal"]
    return [{"label": borough, "value": borough} for borough in ordered]


def get_season_options(data: pd.DataFrame) -> list[dict[str, str]]:
    if data.empty:
        seasons = SEASON_ORDER
    else:
        available = set(data["season"].dropna().unique())
        seasons = [season for season in SEASON_ORDER if season in available]

    return [{"label": season, "value": season} for season in seasons]


def round_up_scale_max(value: float) -> float:
    """Rounds a color scale max upward with readable, tighter breaks.

    Examples:
    - 18 -> 20
    - 68.8 -> 70
    - 138.4 -> 150
    - 180 -> 200
    - 690.5 -> 700
    """
    if value <= 0 or not math.isfinite(value):
        return 1

    magnitude = 10 ** math.floor(math.log10(value))
    normalized = value / magnitude
    nice_steps = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10]

    for step in nice_steps:
        if normalized <= step:
            return step * magnitude

    return 10 * magnitude


def make_empty_figure(message: str) -> go.Figure:
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
        height=620,
        margin={"l": 80, "r": 40, "t": 80, "b": 50},
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    return fig


def make_heatmap_figure(data: pd.DataFrame, selected_season: str, selected_borough: str) -> go.Figure:
    if data.empty:
        return make_empty_figure(
            "Run python preprocess.py first to generate heatmap_viz2.csv."
        )

    filtered = data[
        (data["season"] == selected_season)
        & (data["arrondissement"] == selected_borough)
    ]

    if filtered.empty:
        return make_empty_figure(
            f"No data available for {selected_borough} / {selected_season}."
        )

    rows_by_cell = {
        (int(row.hour), row.day): row
        for row in filtered.itertuples(index=False)
    }

    z_values = []
    hover_text = []

    for hour in HOUR_ORDER:
        z_row = []
        text_row = []
        for day in DAY_ORDER:
            row = rows_by_cell.get((hour, day))
            if row is None:
                z_row.append(None)
                text_row.append(
                    "<br>".join(
                        [
                            f"Borough: {selected_borough}",
                            f"Season: {selected_season}",
                            f"Day: {day}",
                            f"Hour: {hour:02d}:00",
                            "No data available",
                        ]
                    )
                )
            else:
                z_row.append(float(row.mean_volume))
                sample_size = getattr(row, "sample_size", None)
                text = [
                    f"Borough: {selected_borough}",
                    f"Season: {selected_season}",
                    f"Day: {day}",
                    f"Hour: {hour:02d}:00",
                    f"Mean hourly volume per counter: {float(row.mean_volume):.1f} cyclists",
                ]
                if sample_size is not None and pd.notna(sample_size):
                    text.append(f"Counter-hour observations: {int(sample_size)}")
                text_row.append("<br>".join(text))
        z_values.append(z_row)
        hover_text.append(text_row)

    max_value = round_up_scale_max(float(filtered["mean_volume"].max()))

    fig = go.Figure(
        data=go.Heatmap(
            x=DAY_ORDER,
            y=HOUR_LABELS,
            z=z_values,
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
            hoverongaps=True,
            colorscale="YlOrRd",
            zmin=0,
            zmax=max_value,
            colorbar={"title": f"Mean hourly volume<br>scale max: {max_value:g}"},
        )
    )

    fig.update_layout(
        title={
            "text": "Hour x day heatmap - mean cyclist volume",
            "x": 0,
            "xanchor": "left",
        },
        height=620,
        margin={"l": 80, "r": 40, "t": 80, "b": 50},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#1f2933"},
        xaxis={"side": "top", "fixedrange": True},
        yaxis={"title": "Hour of day", "autorange": "reversed", "fixedrange": True},
    )

    return fig


heatmap_data = load_heatmap_data()

app = Dash(__name__)
app.title = "Montreal Cycling Dashboard"

app.layout = html.Main(
    style=PAGE_STYLE,

    children=[
        html.Div(
            style={**CARD_STYLE, "marginBottom": "24px"},
            children=[
                html.H1(
                    "Cycling activity across Montréal",
                    style={"margin": "0 0 6px", "fontSize": "28px"},
                ),
                html.P(
                    "Mean daily cyclist volume per counter by borough, with counting-site bubbles.",
                    style={**NOTE_STYLE, "margin": "0 0 12px"},
                ),
                dcc.Graph(
                    id="viz1-map",
                    figure=make_viz1_figure(show_bubbles=True),
                    config={"displayModeBar": False, "responsive": True},
                ),
            ],
        ),

        html.Div(
            style=CARD_STYLE,
            children=[
                html.H1(
                    "Cycling activity by hour and day",
                    style={"margin": "0 0 6px", "fontSize": "28px"},
                ),
                html.P(
                    "Mean hourly cyclist volume per counter, filtered by season and borough.",
                    style={**NOTE_STYLE, "margin": "0"},
                ),
                html.Div(
                    style=CONTROL_ROW_STYLE,
                    children=[
                        html.Label(
                            style=CONTROL_STYLE,
                            children=[
                                html.Span("Season", style={"fontWeight": "700", "fontSize": "14px"}),
                                dcc.Dropdown(
                                    id="season-dropdown",
                                    options=get_season_options(heatmap_data),
                                    value="All year",
                                    clearable=False,
                                ),
                            ],
                        ),
                        html.Label(
                            style=CONTROL_STYLE,
                            children=[
                                html.Span("Borough", style={"fontWeight": "700", "fontSize": "14px"}),
                                dcc.Dropdown(
                                    id="borough-dropdown",
                                    options=get_borough_options(heatmap_data),
                                    value="All Montréal",
                                    clearable=False,
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Graph(
                    id="viz2-heatmap",
                    config={"displayModeBar": False, "responsive": True},
                ),
                html.P(
                    "Darker cells indicate higher average cyclist volume per counter. "
                    "Weekday activity can reveal commuting peaks, while weekend activity helps "
                    "identify recreational cycling patterns. The season and borough filters allow "
                    "planners to compare how temporal cycling behavior changes across the network.",
                    style={**NOTE_STYLE, "marginTop": "12px"},
                ),
            ],
        )
    ],
)


@app.callback(
    Output("viz2-heatmap", "figure"),
    Input("season-dropdown", "value"),
    Input("borough-dropdown", "value"),
)
def update_heatmap(selected_season: str, selected_borough: str) -> go.Figure:
    return make_heatmap_figure(heatmap_data, selected_season, selected_borough)


if __name__ == "__main__":
    app.run(debug=False)
