from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

# Airbnb-inspired palette. Categorical hues are fixed per room type (never
# cycled) and passed the dataviz validator: lightness band, chroma floor,
# adjacent CVD separation, and 3:1 contrast on white.
CORAL, TEAL, ORANGE, PLUM = "#FF5A5F", "#00A699", "#FC642D", "#914669"
INK, MUTED, LINE, MISSING = "#222222", "#717171", "#EBEBEB", "#B0B0B0"
ROOM_COLORS = {"Entire home/apt": CORAL, "Private room": TEAL, "Hotel room": ORANGE, "Shared room": PLUM}
# Sequential ramps: one hue, light to dark, for magnitude only.
PRICE_SCALE = ["#FFE8E9", "#FFB3B5", "#FF5A5F", "#D93B41", "#8C1D22"]
SHARE_SCALE = ["#E0F5F3", "#80D3CB", "#00A699", "#007A70", "#004D47"]
FONT = "'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def is_missing(value) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def number(value, digits: int = 0) -> str:
    if is_missing(value):
        return "N/A"
    return f"{float(value):,.{digits}f}"


def usd(value, digits: int = 0) -> str:
    if is_missing(value):
        return "N/A"
    # Sign before the currency symbol so A−B deltas read "-$138", not "$-138".
    rounded = round(float(value), digits)
    sign = "-" if rounded < 0 else ""
    return f"{sign}${abs(rounded):,.{digits}f}"


def pct(value, digits: int = 1) -> str:
    if is_missing(value):
        return "N/A"
    return f"{float(value) * 100:.{digits}f}%"


def kept(key: str, default):
    """Last value of a page-local widget. Streamlit drops a widget's state while
    its page is hidden, so widgets re-initialize from this plain copy."""
    return st.session_state.get(f"_keep_{key}", default)


def keep(key: str, value):
    st.session_state[f"_keep_{key}"] = value
    return value


def stat_cards(cards: list[tuple[str, str, str, str]]) -> None:
    """Render (icon, label, value, note) cards: up to four across, stacked on phones."""
    items = "".join(
        f'<div class="stat-card"><span class="stat-icon">{icon}</span>'
        f'<div class="stat-label">{html.escape(label)}</div>'
        f'<div class="stat-value" title="{html.escape(value)}">{html.escape(value)}</div>'
        f'<div class="stat-note">{html.escape(note)}</div></div>'
        for icon, label, value, note in cards
    )
    grid = "stat-grid" if len(cards) >= 4 else "stat-grid two"
    st.markdown(f'<div class="{grid}">{items}</div>', unsafe_allow_html=True)


def metric_cards(row, budget_row, budget: float | None) -> None:
    budget_value = pct(budget_row.within_budget_share) if budget is not None else "Set a budget"
    budget_note = (f"{number(budget_row.within_budget_n)} of {number(budget_row.price_n)} priced · pre-budget"
                   if budget is not None else "Choose a nightly budget above")
    stat_cards([
        ("⌂", "Matching listings", number(row.listing_count), "Snapshot listings meeting all filters"),
        ("$", "Median nightly price", usd(row.median_price), f"Listed USD/night · price_n={number(row.price_n)}"),
        ("✓", "Within nightly budget", budget_value, budget_note),
        ("★", "Reviewed listings", pct(row.reviewed_share), "Share with at least one review"),
    ])


def section(kicker: str, title: str, note: str = "") -> None:
    """Wildfire-style section heading: small coral kicker, large title, side note."""
    side = f'<p>{html.escape(note)}</p>' if note else ""
    st.markdown(
        f'<div class="section-heading"><div><div class="kicker">{html.escape(kicker)}</div>'
        f'<h2>{html.escape(title)}</h2></div>{side}</div>',
        unsafe_allow_html=True,
    )


def panel_header(kicker: str, title: str, note: str = "") -> None:
    foot = f'<p class="panel-note">{html.escape(note)}</p>' if note else ""
    st.markdown(
        f'<div class="panel-kicker">{html.escape(kicker)}</div>'
        f'<h3 class="panel-title">{html.escape(title)}</h3>{foot}',
        unsafe_allow_html=True,
    )


def style_fig(fig, height: int | None = None):
    """Shared Plotly look: recessive grid and axes, ink text, transparent paper."""
    fig.update_layout(
        font=dict(family=FONT, color=INK, size=13), title=None,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="white", bordercolor=LINE, font=dict(family=FONT, color=INK, size=13)),
        margin=dict(l=10, r=10, t=10, b=10), barcornerradius=4,
        legend=dict(font=dict(color=MUTED)),
    )
    fig.update_xaxes(gridcolor=LINE, linecolor=LINE, zeroline=False, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=LINE, linecolor=LINE, zeroline=False, tickfont=dict(color=INK),
                     title_font=dict(color=MUTED, size=12))
    if height:
        fig.update_layout(height=height)
    return fig


def table_formats(frame: pd.DataFrame) -> dict:
    """Display formats for summary tables: whole USD, 1-decimal percentages."""
    formats = {
        **{c: "${:,.0f}" for c in ["median_price", "price_p25", "price_p75"]},
        **{c: lambda v: f"{100 * v:.1f}%" for c in
           ["reviewed_share", "within_budget_share", "pre_budget_within_budget_share"]},
        **{c: "{:,.1f}" for c in ["median_total_reviews", "median_reviews_ltm", "median_available_nights"]},
        "mean_observed_reviews_per_month": "{:.2f}",
    }
    return {c: f for c, f in formats.items() if c in frame.columns}


def add_small_metric_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    checks = [
        ("price_n", "price_n<30"),
        ("review_n", "review_n<30"),
        ("review_ltm_n", "review_ltm_n<30"),
        ("availability_n", "availability_n<30"),
    ]
    result["small_sample_metrics"] = result.apply(
        lambda row: ", ".join(label for col, label in checks if row[col] < 30), axis=1
    )
    return result


def usable_max(series, fallback: float = 1.0) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return fallback
    maximum = float(values.max())
    return maximum if math.isfinite(maximum) and maximum > 0 else fallback
