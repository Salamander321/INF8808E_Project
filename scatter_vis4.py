"""
vis_4.py — Corridor Prioritization Scatter (Plotly + Dash)

Standalone runnable version of Visualization 4 from the mockup.
Run:  python vis_4.py   then open http://127.0.0.1:8050

X-axis  : mean monthly volume per counting sensor (volume_per_sensor)
Y-axis  : winter retention ratio (winter avg / summer avg)
Bubble  : peak-hour demand (7-9h + 16-18h)
Colour  : borough (arrondissement)

Two sliders set threshold lines. Corridors meeting BOTH thresholds are
highlighted (full colour); the rest are dimmed grey.

This file owns its own data prep so it runs on its own. When you fold it
into the tabbed dashboard, drop `prepare_scatter_data` / the loaders and
pass the prepared `scatter_df` in instead.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from preprocess import load_scatter_df



SEASON_COMPARE = "Summer"           # the "non-winter" reference season

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
}

X_COL = "volume_per_sensor"



# --------------------------------------------------------------------------
# Figure builder
# --------------------------------------------------------------------------
PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8", "#ffbb78",
    "#98df8a", "#ff9896", "#c5b0d5", "#c49c94", "#f7b6d2", "#dbdb8d",
]
SIZE_MIN, SIZE_MAX = 8, 46  # marker diameter range (px)


def _rgba(hex_color: str, alpha: float) -> str:
    """Convert '#rrggbb' to an 'rgba(r,g,b,a)' string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _sizes(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(SIZE_MIN + (SIZE_MAX - SIZE_MIN) / 2, index=series.index)
    return SIZE_MIN + (SIZE_MAX - SIZE_MIN) * (series - lo) / (hi - lo)


def build_figure(df: pd.DataFrame, vol_thresh: float, ret_thresh: float) -> go.Figure:
    df = df.copy()
    df["sz"] = _sizes(df["peak_volume"])
    df["highlighted"] = (df[X_COL] >= vol_thresh) & (df["winter_retention"] >= ret_thresh)

    boroughs = sorted(df["arrondissement"].unique())
    color_map = {b: PALETTE[i % len(PALETTE)] for i, b in enumerate(boroughs)}

    fig = go.Figure()

    hover = (
        "<b>%{customdata[0]}</b><br>"
        "Borough: %{customdata[1]}<br>"
        "Volume / sensor: %{x:,.0f}<br>"
        "Winter retention: %{y:.2f}<br>"
        "Peak-hour demand: %{customdata[2]:.1f}"
        "<extra></extra>"
    )


    HI_ALPHA, DIM_ALPHA = 0.95, 0.22
    for b in boroughs:
        sub = df[df["arrondissement"] == b]
        if not len(sub):
            continue
        base = color_map[b]
        point_colors = [
            _rgba(base, HI_ALPHA if h else DIM_ALPHA)
            for h in sub["highlighted"]
        ]
        edge_w = sub["highlighted"].map({True: 1.0, False: 0.0}).values

        # Legend-only trace: a single solid swatch in the borough colour.
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", name=b, legendgroup=b,
            marker=dict(size=12, color=base),
            showlegend=True, hoverinfo="skip",
        ))
        # Real data trace: per-point faded/solid colours, hidden from legend.
        fig.add_trace(go.Scatter(
            x=sub[X_COL], y=sub["winter_retention"],
            mode="markers", name=b, legendgroup=b, showlegend=False,
            marker=dict(
                size=sub["sz"], color=point_colors,
                line=dict(width=edge_w, color="white"),
            ),
            customdata=sub[["corridor", "arrondissement", "peak_volume"]].values,
            hovertemplate=hover,
        ))

    # Threshold lines
    fig.add_vline(x=vol_thresh, line=dict(color="grey", width=1, dash="dash"))
    fig.add_hline(y=ret_thresh, line=dict(color="grey", width=1, dash="dash"))

    # Invest-here zone shading (top-right of both thresholds)
    fig.add_shape(
        type="rect", x0=vol_thresh, x1=df[X_COL].max() * 1.05,
        y0=ret_thresh, y1=df["winter_retention"].max() * 1.05,
        fillcolor="rgba(44,160,44,0.06)", line_width=0, layer="below",
    )
    fig.add_annotation(
        x=vol_thresh, y=df["winter_retention"].max(),
        xanchor="left", yanchor="top", xshift=6,
        text="Invest-here zone<br>high volume + year-round",
        showarrow=False, align="left", font=dict(size=10, color="#2ca02c"),
    )

    fig.update_layout(
        title=dict(
            text="Corridor prioritization — Volume vs year-round usage"
                 "<br><sup>Bubble size = peak-hour demand · Colour = borough</sup>",
            x=0.5, xanchor="center",
        ),
        xaxis_title="Mean monthly cyclist volume per sensor",
        yaxis_title="Winter retention ratio (winter / summer)",
        # Legend as a separate panel to the RIGHT of the plotting area.
        legend=dict(
            title="Borough", bgcolor="rgba(255,255,255,0)",
            yanchor="top", y=1, xanchor="left", x=1.02,
            itemsizing="constant",
        ),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color="black"), height=640,
        margin=dict(l=70, r=240, t=80, b=60),
    )
    fig.update_xaxes(showline=True, linecolor="black", gridcolor="#eee", zeroline=False)
    fig.update_yaxes(showline=True, linecolor="black", gridcolor="#eee", zeroline=False)
    return fig



scatter_df = load_scatter_df()
VOL_MIN, VOL_MAX = float(scatter_df[X_COL].min()), float(scatter_df[X_COL].max())
RET_MIN, RET_MAX = float(scatter_df["winter_retention"].min()), float(scatter_df["winter_retention"].max())
VOL_DEFAULT = VOL_MIN
RET_DEFAULT = RET_MIN   

app = Dash(__name__)
app.layout = html.Div(
    style={"maxWidth": "1100px", "margin": "0 auto", "fontFamily": "Arial, sans-serif"},
    children=[
        dcc.Graph(id="scatter", config={"displayModeBar": True}),
        html.Div(
            style={"display": "flex", "gap": "40px", "padding": "10px 30px 30px"},
            children=[
                html.Div(style={"flex": 1}, children=[
                    html.Label("Mean cyclist volume threshold", style={"fontWeight": "bold"}),
                    dcc.Slider(
                        id="vol-slider", min=VOL_MIN, max=VOL_MAX, value=VOL_DEFAULT,
                        marks=None, tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ]),
                html.Div(style={"flex": 1}, children=[
                    html.Label("Winter retention threshold", style={"fontWeight": "bold"}),
                    dcc.Slider(
                        id="ret-slider", min=RET_MIN, max=RET_MAX, value=RET_DEFAULT,
                        marks=None, step=0.01,
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ]),
            ],
        ),
    ],
)


@app.callback(
    Output("scatter", "figure"),
    Input("vol-slider", "value"),
    Input("ret-slider", "value"),
)
def update(vol_thresh, ret_thresh):
    return build_figure(scatter_df, vol_thresh, ret_thresh)


if __name__ == "__main__":
    app.run(debug=True)