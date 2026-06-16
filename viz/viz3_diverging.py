"""
viz/viz3_diverging.py
=====================
Visualization 3 — Directional peak-hour flow: diverging bar charts.
 
Two side-by-side subplots (AM peak 7-9h PM peak 16-18h).
Each corridor is one row; bars extend left for Inbound (Sud/Est)
and right for Outbound (Nord/Ouest).
 
Called from app.py via make_viz3_figure(selected_corridors).
"""
 
from pathlib import Path
 
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 
 
VIZ3_DATA_PATH = Path("diverging_viz3.csv")
 
# Montreal blue palette — dark for Inbound, light for Outbound
COLOR_INBOUND  = "#1a4f8a"   # dark blue  (toward downtown)
COLOR_OUTBOUND = "#8ab4d8"   # light blue (away from downtown)
 
TOP_N_DEFAULT = 8
 
 
# ── Data loading ─────────────────────────────────────────────────────────────
 
def load_viz3_data() -> pd.DataFrame:
    if not VIZ3_DATA_PATH.exists():
        return pd.DataFrame()
 
    df = pd.read_csv(VIZ3_DATA_PATH)
    df["mean_volume"] = pd.to_numeric(df["mean_volume"], errors="coerce")
    df = df.dropna(subset=["corridor", "peak", "flow", "mean_volume"])
    return df
 
 
def get_top_corridors(df: pd.DataFrame, n: int = TOP_N_DEFAULT) -> list[str]:
    """Returns the top-n corridors ranked by total mean volume across both peaks."""
    if df.empty:
        return []
    totals = (
        df.groupby("corridor")["mean_volume"]
        .sum()
        .sort_values(ascending=False)
    )
    return totals.head(n).index.tolist()
 
 
def get_all_corridors(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    totals = (
        df.groupby("corridor")["mean_volume"]
        .sum()
        .sort_values(ascending=False)
    )
    return totals.index.tolist()
 
 
# ── Figure builder ────────────────────────────────────────────────────────────
 
def make_viz3_figure(selected_corridors: list[str] | None = None) -> go.Figure:
    df = load_viz3_data()
 
    if df.empty:
        return _empty_figure(
            "Run python preprocess.py first to generate diverging_viz3.csv."
        )
 
    if not selected_corridors:
        selected_corridors = get_top_corridors(df)
 
    # Filter to selected corridors
    df = df[df["corridor"].isin(selected_corridors)].copy()
 
    if df.empty:
        return _empty_figure("No data for the selected corridors.")
 
    # Sort corridors by total mean volume ascending (so highest is at top of chart)
    corridor_order = (
        df.groupby("corridor")["mean_volume"]
        .sum()
        .sort_values(ascending=True)   # ascending = top of y-axis is highest
        .index.tolist()
    )
 
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["AM Peak (7h–9h), toward downtown",
                        "PM Peak (16h–18h). away from downtown"],
        shared_yaxes=True,
        horizontal_spacing=0.04,
    )
 
    for col_idx, peak in enumerate(["AM", "PM"], start=1):
        peak_df = df[df["peak"] == peak]
 
        for flow, color, x_sign in [
            ("Inbound",  COLOR_INBOUND,  -1),   # left side
            ("Outbound", COLOR_OUTBOUND, +1),   # right side
        ]:
            flow_df = peak_df[peak_df["flow"] == flow].set_index("corridor")
 
            x_vals = []
            y_vals = []
            hover_texts = []
 
            for corridor in corridor_order:
                if corridor in flow_df.index:
                    vol = float(flow_df.loc[corridor, "mean_volume"])
                    sample = flow_df.loc[corridor, "sample_size"] if "sample_size" in flow_df.columns else None
                else:
                    vol = 0.0
                    sample = None
 
                x_vals.append(x_sign * vol)
                y_vals.append(corridor)
 
                direction_label = "Sud / Est (inbound)" if flow == "Inbound" else "Nord / Ouest (outbound)"
                tooltip_lines = [
                    f"<b>{corridor}</b>",
                    f"Peak: {peak} ({'7h–9h' if peak == 'AM' else '16h–18h'})",
                    f"Flow: {flow} ({direction_label})",
                    f"Mean volume: {vol:.1f} cyclists/h",
                ]
                if sample is not None and pd.notna(sample):
                    tooltip_lines.append(f"Counter-hour observations: {int(sample)}")
                hover_texts.append("<br>".join(tooltip_lines))
 
            show_legend = (col_idx == 1)  # only show legend items for AM panel
 
            fig.add_trace(
                go.Bar(
                    x=x_vals,
                    y=y_vals,
                    orientation="h",
                    name=flow,
                    marker_color=color,
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=hover_texts,
                    showlegend=show_legend,
                    legendgroup=flow,
                ),
                row=1,
                col=col_idx,
            )
 
    # ── Axis configuration ───────────────────────────────────────────────────
    # Compute a symmetric x range across both panels for visual fairness
    max_abs = df["mean_volume"].max()
    x_range_max = _nice_ceil(max_abs * 1.05)
 
    # AM panel (col 1) — inbound is negative, outbound positive in our encoding,
    # but we want the LEFT side to visually show inbound.
    # Both panels share the same ±range so amplitudes are comparable.
    axis_common = dict(
        zeroline=True,
        zerolinecolor="#1f2933",
        zerolinewidth=1.5,
        tickvals=_symmetric_ticks(x_range_max),
        ticktext=[str(abs(v)) for v in _symmetric_ticks(x_range_max)],
        range=[-x_range_max, x_range_max],
        fixedrange=True,
        gridcolor="#e8ecf0",
    )
 
    fig.update_xaxes(title_text="Mean volume (cyclists/h)", **axis_common, row=1, col=1)
    fig.update_xaxes(title_text="Mean volume (cyclists/h)", **axis_common, row=1, col=2)
    fig.update_yaxes(
        title_text="",
        autorange=True,
        tickfont={"size": 11},
        fixedrange=True,
        row=1, col=1,
    )
 
    # Shared subtitle note
    n_corridors = len(corridor_order)
    subtitle = (
        f"Directional flow at peak hours - {n_corridors} corridor{'s' if n_corridors != 1 else ''} selected<br>"
        "<sup>Inbound = toward downtown (Sud/Est)  ·  Outbound = away from downtown (Nord/Ouest)</sup>"
    )
 
    fig.update_layout(
        title={
            "text": subtitle,
            "x": 0,
            "xanchor": "left",
            "font": {"size": 14},
        },
        height=max(480, 80 + 36 * n_corridors),
        margin={"l": 20, "r": 20, "t": 110, "b": 60},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#1f2933", "family": "Inter, Arial, sans-serif"},
        barmode="overlay",
        bargap=0.28,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.18,
            "xanchor": "center",
            "x": 0.5,
            "title": {"text": ""},
        },
    )
 
    # Light grey panel backgrounds
    fig.update_layout(
        plot_bgcolor="#f9fafb",
    )
 
    return fig
 
 
# ── Helpers ──────────────────────────────────────────────────────────────────
 
def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font={"size": 15, "color": "#5f6b7a"},
        align="center",
    )
    fig.update_layout(
        height=480,
        margin={"l": 20, "r": 20, "t": 80, "b": 40},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig
 
 
def _nice_ceil(value: float) -> float:
    """Round up to a clean axis bound (10, 25, 50, 75, 100, 150 …)."""
    if value <= 0:
        return 10
    import math
    mag = 10 ** math.floor(math.log10(value))
    norm = value / mag
    for step in [1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8, 10]:
        if norm <= step:
            return step * mag
    return 10 * mag
 
 
def _symmetric_ticks(x_max: float) -> list[float]:
    """Return 5 evenly-spaced ticks from -x_max to +x_max."""
    step = x_max / 2
    return [-x_max, -step, 0, step, x_max]