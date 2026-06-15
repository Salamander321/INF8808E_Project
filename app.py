# """
# app.py — Single Dash app for the Montréal Cycling dashboard.

# INF8808 structure: this is the one entry point. Each visualization lives in
# its own figure-only module (scatter.py, heatmap.py, ...) that exposes pure
# functions. This file builds ONE layout with three tabs (Where / When / What)
# and registers ALL callbacks on the single `app` object.

# Run via the failsafe wrapper:   python server.py   -> http://127.0.0.1:8050
# (or directly:                   python app.py)
# """

from json import load

import dash
from dash import Input, Output, dcc, html
import load_data

import visualizations.scatter as scatter            
import visualizations.heatmap as heatmap          

           
_HAS_HEATMAP = True

try:
    import visualizations.choropleth as choropleth         #
    _HAS_CHOROPLETH = True
except Exception:             # noqa: BLE001
    _HAS_CHOROPLETH = False

try:
    import visualizations.diverging as diverging         
    _HAS_DIVERGING = True
except Exception:             # noqa: BLE001
    _HAS_DIVERGING = False


print(_HAS_HEATMAP)

# --------------------------------------------------------------------------
# Data — loaded once at startup, shared across the app.
# --------------------------------------------------------------------------
SCATTER_DF = load_data.load_scatter_data()
BOUNDS = scatter.get_bounds(SCATTER_DF)


HEATMAP_DF = load_data.load_heatmap_data()

# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
PAGE_STYLE = {
    "maxWidth": "1280px", "margin": "24px auto", "padding": "0 20px",
    "fontFamily": "Inter, Arial, sans-serif", "color": "#1f2933",
}
NOTE = {"color": "#5f6b7a", "fontSize": "14px"}
PLACEHOLDER = {
    "display": "flex", "alignItems": "center", "justifyContent": "center",
    "height": "320px", "border": "1px dashed #c4ccd6", "borderRadius": "8px",
    "color": "#5f6b7a", "background": "#fafbfc", "textAlign": "center",
}


def placeholder(label: str) -> html.Div:
    return html.Div(style=PLACEHOLDER, children=html.Div([
        html.Div(f"{label} is not built yet.", style={"fontWeight": "700"}),
        html.Div("Add its module and it will appear here.", style=NOTE),
    ]))


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Montréal Cycling Dashboard"

GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


# ---- Tab builders --------------------------------------------------------
def where_tab() -> html.Div:
    if _HAS_CHOROPLETH:
        content = dcc.Graph(id="vis1-choropleth",
                            figure=choropleth.get_figure(),  # adjust to its API
                            config=GRAPH_CONFIG)
    else:
        content = placeholder("Vis 1 — choropleth + bubble overlay")
    return html.Div(style={"padding": "20px 0"}, children=[
        html.P("Geographic distribution of cycling activity across the island.",
               style=NOTE),
        content,
    ])


def when_tab() -> html.Div:
    if _HAS_HEATMAP:
        heatmap_block = html.Div([
            html.Div(style={"display": "flex", "gap": "16px",
                            "flexWrap": "wrap", "margin": "12px 0"}, children=[
                html.Label([html.Span("Season ", style={"fontWeight": "700"}),
                            dcc.Dropdown(id="hm-season",
                                         options=heatmap_season_options(),
                                         value="All year", clearable=False,
                                         style={"minWidth": "220px"})]),
                html.Label([html.Span("Borough ", style={"fontWeight": "700"}),
                            dcc.Dropdown(id="hm-borough",
                                         options=heatmap_borough_options(),
                                         value="All Montréal", clearable=False,
                                         style={"minWidth": "220px"})]),
            ]),
            dcc.Graph(id="vis2-heatmap", config=GRAPH_CONFIG),
        ])
    else:
        heatmap_block = placeholder("Seasonal Heatmap")

    diverging_block = (
        dcc.Graph(id="vis3-diverging", figure=diverging.get_figure(),
                  config=GRAPH_CONFIG)
        if _HAS_DIVERGING else placeholder("Vis 3 — diverging bar chart")
    )

    return html.Div(style={"padding": "20px 0", "display": "grid", "gap": "28px"},
                    children=[
        html.P("Usage patterns across hourly, daily, and seasonal dimensions.",
               style=NOTE),
        html.Div([html.H3("Seasonal Heatmap",
                          style={"margin": "0 0 8px"}), heatmap_block]),
        html.Div([html.H3("Vis 3 — Directional peak-hour flow",
                          style={"margin": "0 0 8px"}), diverging_block]),
    ])


def what_tab() -> html.Div:
    return html.Div(style={"padding": "20px 0"}, children=[
        html.P("Corridors combining high volume, peak demand, and year-round "
               "usage.", style=NOTE),
        dcc.Graph(id="vis4-scatter", config=GRAPH_CONFIG),
        html.Div(style={"display": "flex", "gap": "40px",
                        "padding": "10px 0 0"}, children=[
            html.Div(style={"flex": 1}, children=[
                html.Label("Mean cyclist volume threshold",
                           style={"fontWeight": "700"}),
                dcc.Slider(id="vol-slider",
                           min=BOUNDS["vol_min"], max=BOUNDS["vol_max"],
                           value=BOUNDS["vol_default"], marks=None,
                           step=max(1, round((BOUNDS["vol_max"] - BOUNDS["vol_min"]) / 200)),
                           tooltip={"placement": "bottom", "always_visible": True,
                                    "template": "{value:,.0f}"}),
            ]),
            html.Div(style={"flex": 1}, children=[
                html.Label("Winter retention threshold",
                           style={"fontWeight": "700"}),
                dcc.Slider(id="ret-slider",
                           min=BOUNDS["ret_min"], max=BOUNDS["ret_max"],
                           value=BOUNDS["ret_default"], step=0.01, marks=None,
                           tooltip={"placement": "bottom", "always_visible": True,
                                    "template": "{value:.2f}"}),
            ]),
        ]),
    ])


# ---- Heatmap dropdown options (only if module present) -------------------
def heatmap_season_options():
    return heatmap.get_season_options(HEATMAP_DF) \
        if hasattr(heatmap, "get_season_options") else []


def heatmap_borough_options():
    return heatmap.get_borough_options(HEATMAP_DF) \
        if hasattr(heatmap, "get_borough_options") else []


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
app.layout = html.Main(style=PAGE_STYLE, children=[
    html.H1("Evidence-Based Insights for Montréal's Cycling Network",
            style={"fontSize": "26px", "margin": "0 0 4px"}),
    html.P("INF8808E - Team1", style={**NOTE, "margin": "0 0 12px"}),
    dcc.Tabs(id="main-tabs", value="where", children=[
        dcc.Tab(label="Where?", value="where"),
        dcc.Tab(label="When?", value="when"),
        dcc.Tab(label="What?", value="what"),
    ]),
    html.Div(id="tab-content"),
])


# --------------------------------------------------------------------------
# Callbacks — all registered on the single app
# --------------------------------------------------------------------------
@app.callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab):
    return {"where": where_tab, "when": when_tab, "what": what_tab}[tab]()


@app.callback(
    Output("vis4-scatter", "figure"),
    Input("vol-slider", "value"),
    Input("ret-slider", "value"),
)
def update_scatter(vol_thresh, ret_thresh):
    return scatter.build_figure(SCATTER_DF, vol_thresh, ret_thresh)


@app.callback(
        Output("vis2-heatmap", "figure"),
        Input("hm-season", "value"),
        Input("hm-borough", "value"),
)
def update_heatmap(season, borough):
    return heatmap.make_heatmap_figure(
        HEATMAP_DF, season, borough)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True)