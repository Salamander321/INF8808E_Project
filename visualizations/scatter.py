
import pandas as pd
import plotly.graph_objects as go
# --------------------------------------------------------------------------
# Config — point these at your real data files / aggregation source.
# --------------------------------------------------------------------------

X_COL = "mean_volume"
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

    # One trace per borough holding ALL its corridors. Highlighted points
    # render at full strength; dimmed points keep the SAME borough hue but
    # faded (e.g. red -> light red). The fade is baked into a per-point rgba
    # colour, while the trace's base `marker.color` stays solid so the legend
    # swatch shows the true borough colour. Every borough appears once in the
    # legend regardless of highlight state.
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

    # --- Dynamic axis ranges -------------------------------------------------
    # Use a robust (percentile-clipped) range so a single extreme outlier does
    # not squash the dense cluster. The threshold line is always kept in view,
    # and the range adapts as sliders move. Outliers beyond the clip still plot
    # but the axis no longer stretches to fit them.
    def _range(values: pd.Series, thresh: float,
               lo_q: float = 0.0, hi_q: float = 0.97, pad_frac: float = 0.08):
        lo = min(values.quantile(lo_q), thresh)
        hi = max(values.quantile(hi_q), thresh)
        span = (hi - lo) or (abs(hi) or 1.0)
        return [lo - span * pad_frac, hi + span * pad_frac]

    x_range = _range(df[X_COL], vol_thresh)
    y_range = _range(df["winter_retention"], ret_thresh)

    # Threshold lines (drawn within the visible range)
    fig.add_vline(x=vol_thresh, line=dict(color="grey", width=1, dash="dash"))
    fig.add_hline(y=ret_thresh, line=dict(color="grey", width=1, dash="dash"))

    # Invest-here zone shading (top-right of both thresholds, clipped to view)
    fig.add_shape(
        type="rect", x0=vol_thresh, x1=x_range[1],
        y0=ret_thresh, y1=y_range[1],
        fillcolor="rgba(44,160,44,0.06)", line_width=0, layer="below",
    )
    fig.add_annotation(
        x=vol_thresh, y=y_range[1],
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
        yaxis_title="Winter retention ratio (winter / Non Winter volume)",
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
    fig.update_xaxes(showline=True, linecolor="black", gridcolor="#eee",
                     zeroline=False, range=x_range)
    fig.update_yaxes(showline=True, linecolor="black", gridcolor="#eee",
                     zeroline=False, range=y_range)
    return fig


def get_bounds(df: pd.DataFrame) -> dict:
    """Slider min/max/default for the two thresholds, derived from the data."""
    return {
        "vol_min": float(df[X_COL].min()),
        "vol_max": float(df[X_COL].max()),
        "vol_default": float(df[X_COL].median()),
        "ret_min": float(df["winter_retention"].min()),
        "ret_max": float(1.5),
        "ret_default": float(df["winter_retention"].median()),
    }