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
import visualizations.map as map         #
import visualizations.diverging as diverging         
          # noqa: BLE001

_HAS_DIVERGING = True
_HAS_HEATMAP = True
_HAS_MAP = True

# --------------------------------------------------------------------------
# Data — loaded once at startup, shared across the app.
# --------------------------------------------------------------------------
MAP_DF = load_data.load_map_data()
MAP_GEOJSON = load_data.load_borough_geojson()


HEATMAP_DF = load_data.load_heatmap_data()
SCATTER_DF = load_data.load_scatter_data()
DIVERGING_DF = load_data.load_diverging_data()
BOUNDS = scatter.get_bounds(SCATTER_DF)



# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
PAGE_STYLE = {
    "maxWidth": "1280px", "margin": "24px auto", "padding": "0 20px",
    "fontFamily": "Inter, Arial, sans-serif", "color": "#1f2933",
}
NOTE = {"color": "#5f6b7a", "fontSize": "20px"}

PLACEHOLDER = {
    "display": "flex", "alignItems": "center", "justifyContent": "center",
    "height": "320px", "border": "1px dashed #c4ccd6", "borderRadius": "8px",
    "color": "#5f6b7a", "background": "#fafbfc", "textAlign": "center",
}

CARD_STYLE = {
    "background": "#ffffff",
    "border": "1px solid #d8dee7",
    "borderRadius": "8px",
    "padding": "24px",
    "boxShadow": "0 1px 2px rgba(15, 23, 42, 0.06)",
}
NOTE_STYLE = {
    "color": "#5f6b7a",
    "fontSize": "20px",
    "lineHeight": "1.5",
}

def placeholder(label: str) -> html.Div:
    return html.Div(style=PLACEHOLDER, children=html.Div([
        html.Div(f"{label} is not built yet.", style={"fontWeight": "700"}),
        html.Div("It will appear once it is built and integrated. CIAO !!!", style=NOTE),
    ]))


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Montréal Cycling Dashboard"

GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


# ---- Tab builders --------------------------------------------------------
def where_tab() -> html.Div:
    if _HAS_MAP:
        content = html.Div([
            html.P("Each borough is shaded by its mean daily cyclist volume per counter — darker means more cycling. " \
                "Bubbles mark individual counting sites, sized by volume. Toggle the bubbles on or off to switch between" \
                " borough-level patterns and corridor-level detail.",
                style={**NOTE_STYLE, "margin": "6px 0 0"}),
            dcc.Checklist(
                id="map-bubbles",
                options=[{"label": "Counting sites", "value": "on"}],
                value=["on"],          # checked by default -> bubbles visible
                style={"margin": "8px 0"},
            ),
            dcc.Graph(id="vis1-choropleth", config=GRAPH_CONFIG),
            html.P("Cycling activity concentrates sharply in the central boroughs around Ville-Marie and Le Plateau, and " \
                "drops off toward the periphery — a few central corridors carry a large share of the network's traffic.",
                style={**NOTE_STYLE, "margin": "6px 0 0"}),
        ])
    else:
        content = placeholder("Vis 1 — choropleth + bubble overlay")
    return html.Div(style={"padding": "20px 0"}, children=[
        html.H2("Geographic distribution of cycling activity across the island."),
        content,
    ])


def when_tab() -> html.Div:
    if _HAS_HEATMAP:
        heatmap_block = html.Div([
            # html.P("Mean hourly cyclist volume per counter, filtered by season and borough.",
            #         style={**NOTE_STYLE, "margin": "0"}),
            html.P("This visualization examines when cycling demand is highest and how daily "
                    "patterns vary by season and borough. It helps identify weekday commuting "
                    "peaks, broader weekend activity, and locations where cycling rhythms "
                    "differ from the Montréal-wide pattern.",
                    style={**NOTE_STYLE, "margin": "6px 0 0"}),



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
        
            html.P("Each cell is the mean hourly cyclist volume per counter for one "
                    "day-of-week and hour combination, averaged across all dates matching "
                    "the selected filters.",
                    style={**NOTE_STYLE, "margin": "6px 0 0"}),
        ])
    else:
        heatmap_block = placeholder("Seasonal Heatmap")

    if _HAS_DIVERGING:
        diverging_block = html.Div([
            html.P("Mean cyclist volume per counter during AM (7h–9h) and PM (16h–18h) "
                    "peaks, split by direction: inbound (toward downtown) vs outbound.",
                    style={**NOTE_STYLE, "margin": "0 0 8px"}),
            html.Label(
                style={"display": "block", "margin": "12px 0"},
                children=[
                    html.Span("Corridors ", style={"fontWeight": "700"}),
                    dcc.Dropdown(
                        id="dv-corridors",
                        options=[{"label": c, "value": c}
                                for c in diverging.get_all_corridors(DIVERGING_DF)],
                        value=diverging.get_top_corridors(DIVERGING_DF),
                        multi=True,
                        clearable=False,
                        placeholder="Select corridors…",
                    ),
                ],
            ),
            dcc.Graph(id="vis3-diverging", config=GRAPH_CONFIG),
            html.P("Bars left = inbound (Sud/Est, toward downtown); bars right = outbound "
                    "(Nord/Ouest).",
                style={**NOTE_STYLE, "marginTop": "12px"}),
        ])
    else:
        diverging_block = placeholder("Diverging peak-hour Barchart")

    return html.Div(style={"padding": "20px 0", "display": "grid", "gap": "28px"},
                    children=[
        # html.P("Usage patterns across hourly, daily, and seasonal dimensions.",
        #        style=NOTE),
        html.Div([html.H2("Seasonal Heatmap",
                          style={"margin": "0 0 8px"}), heatmap_block]),
        html.Div([html.H2("Diverging peak-hour barchart",
                          style={"margin": "0 0 8px"}), diverging_block]),
    ])


def what_tab() -> html.Div:
    return html.Div(style={"padding": "20px 0"}, children=[

        # html.P("Corridors combining high volume, peak demand, and year-round "
        #        "usage.", style=NOTE),
        html.H2("Identifying corridors with high, consistent demand throughout the year.", style={"margin": "0 0 8px"}),

        html.P("Each bubble is a corridor: x = year-round volume per counter, y = how much of its non-winter ridership it keeps through winter, size = peak-hour demand, colour = borough. " \
            "Drag the two sliders to set your own thresholds — corridors clearing both are highlighted as investment candidates while the rest fade back",
             style={**NOTE_STYLE, "margin": "0 "}),

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
                        #    tooltip={"placement": "bottom", "always_visible": True,
                                    # "template": "{value:,.0f}"}
                                    ),
            ]),
            html.Div(style={"flex": 1}, children=[
                html.Label("Winter retention threshold",
                           style={"fontWeight": "700"}),
                dcc.Slider(id="ret-slider",
                           min=BOUNDS["ret_min"], max=BOUNDS["ret_max"],
                           value=BOUNDS["ret_default"], step=0.01, marks=None,
                        #    tooltip={"placement": "bottom", "always_visible": False,}
                                    ),
            ]),
        ]),
    ])


# ---- Heatmap dropdown options  -------------------
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
            style={"fontSize": "34px", "margin": "0 0 4px"}),
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
    Output("vis1-choropleth", "figure"),
    Input("map-bubbles", "value"),
)
def update_map(bubble_value):
    show = "on" in (bubble_value or [])
    return map.get_figure(MAP_DF, MAP_GEOJSON, show)

@app.callback(
        Output("vis2-heatmap", "figure"),
        Input("hm-season", "value"),
        Input("hm-borough", "value"),
)
def update_heatmap(season, borough):
    return heatmap.make_heatmap_figure(
        HEATMAP_DF, season, borough)

@app.callback(
    Output("vis3-diverging", "figure"),
    Input("dv-corridors", "value"),
)
def update_diverging(selected_corridors):
    return diverging.get_figure(DIVERGING_DF, selected_corridors or [])


@app.callback(
    Output("vis4-scatter", "figure"),
    Input("vol-slider", "value"),
    Input("ret-slider", "value"),
)
def update_scatter(vol_thresh, ret_thresh):
    return scatter.build_figure(SCATTER_DF, vol_thresh, ret_thresh)



server = app.server

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True)