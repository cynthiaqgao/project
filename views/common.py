from __future__ import annotations

import html
import math
from urllib.parse import quote

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


LANDMARKS = {"Downtown LA": (34.0522, -118.2437), "Santa Monica beach": (34.0100, -118.4960),
             "LAX airport": (33.9416, -118.4085)}


def miles(lat, lon, point) -> float:
    """Straight-line (great-circle) miles; not driving or transit time."""
    if is_missing(lat) or is_missing(lon):
        return float("nan")
    p1, p2 = math.radians(float(lat)), math.radians(point[0])
    dp, dl = p2 - p1, math.radians(point[1] - float(lon))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def airbnb_search(area: str, room: str | None = None, budget: float | None = None) -> str:
    """Airbnb search URL for a neighborhood, carrying room type and budget when set."""
    params = []
    if room:
        params.append("room_types%5B%5D=" + quote(room, safe=""))
    if budget is not None:
        params.append(f"price_max={int(budget)}")
    url = f"https://www.airbnb.com/s/{quote(f'{area}, Los Angeles, CA', safe='')}/homes"
    return url + ("?" + "&".join(params) if params else "")


def info(text: str) -> str:
    """Hover/focus ⓘ icon that keeps definitions and formulas out of the way."""
    return (f'<span class="info" tabindex="0" aria-label="{html.escape(text)}">i'
            f'<span class="tip">{html.escape(text)}</span></span>')


def stat_cards(cards: list[tuple]) -> None:
    """Render (icon, label, value, note[, tip]) cards: up to four across, stacked on phones."""
    items = "".join(
        f'<div class="stat-card"><span class="stat-icon">{card[0]}</span>'
        f'<div class="stat-label">{html.escape(card[1])}{info(card[4]) if len(card) > 4 and card[4] else ""}</div>'
        f'<div class="stat-value" title="{html.escape(card[2])}">{html.escape(card[2])}</div>'
        f'<div class="stat-note">{html.escape(card[3])}</div></div>'
        for card in cards
    )
    grid = "stat-grid" if len(cards) >= 4 else "stat-grid two"
    st.markdown(f'<div class="{grid}">{items}</div>', unsafe_allow_html=True)


def metric_cards(row, budget_row, budget: float | None, room: str = "places") -> None:
    budget_set = budget is not None
    noun = {"Entire home/apt": "entire homes", "Private room": "private rooms", "Hotel room": "hotel rooms",
            "Shared room": "shared rooms"}.get(room, "places")
    stat_cards([
        ("⌂", "Places to stay", number(row.listing_count), "Match your filters",
         f"{number(row.listing_count)} {noun} in the snapshot match every filter you set."),
        ("$", "Typical price", usd(row.median_price), "per night",
         f"Half of the matching {noun} list for less than {usd(row.median_price)} a night and half for more. "
         f"Taxes, cleaning and service fees are extra. {number(row.missing_price_n)} have no listed price "
         "and are left out."),
        ("✓", "Fits your budget", pct(budget_row.within_budget_share) if budget_set else "—",
         f"{number(budget_row.within_budget_n)} of {number(budget_row.price_n)} places" if budget_set
         else "Slide the budget above",
         (f"Out of {number(budget_row.price_n)} {noun} with a price, {number(budget_row.within_budget_n)} are "
          f"listed at {usd(budget)}/night or less." if budget_set else
          "Set a nightly budget to see what share of places fit it.")),
        ("★", "Have reviews", pct(row.reviewed_share), "At least one guest review",
         f"{pct(row.reviewed_share)} of these {noun} have at least one guest review, so someone has stayed "
         "and written about it. It is a count, not a star rating."),
    ])


def section(kicker: str, title: str, tip: str = "") -> None:
    """Section heading: small coral kicker over a large title."""
    st.markdown(
        f'<div class="section-heading"><div><div class="kicker">{html.escape(kicker)}</div>'
        f'<h2>{html.escape(title)}{info(tip) if tip else ""}</h2></div></div>',
        unsafe_allow_html=True,
    )


def panel_header(kicker: str, title: str, tip: str = "") -> None:
    st.markdown(
        f'<div class="panel-kicker">{html.escape(kicker)}</div>'
        f'<h3 class="panel-title">{html.escape(title)}{info(tip) if tip else ""}</h3>',
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
