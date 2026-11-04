from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .common import CORAL, INK, TEAL, airbnb_search, info, number, panel_header, pct, style_fig, usd


def _range_chart(a: pd.Series, b: pd.Series):
    """Middle-50% price range with the median marked, A above B, shared USD axis from 0."""
    fig = go.Figure()
    for row, color, role in ((a, CORAL, "A"), (b, TEAL, "B")):
        if pd.isna(row.median_price):
            continue
        label = f"{role} · {row.neighbourhood}"
        fig.add_trace(go.Scatter(
            x=[row.price_p25, row.price_p75], y=[label, label], mode="lines",
            line=dict(color=color, width=10), opacity=.35, showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[row.median_price], y=[label], mode="markers+text", name=label,
            marker=dict(color=color, size=16, line=dict(color="white", width=2)),
            text=[usd(row.median_price)], textposition="top center", textfont=dict(color=INK, size=13),
            hovertemplate=(f"<b>{html.escape(str(row.neighbourhood))}</b><br>Typical ${row.median_price:,.0f}/night"
                           f"<br>Most places ${row.price_p25:,.0f}–${row.price_p75:,.0f}<extra></extra>"),
        ))
    upper = max(float(a.price_p75) if pd.notna(a.price_p75) else 0, float(b.price_p75) if pd.notna(b.price_p75) else 0)
    style_fig(fig, height=230)
    fig.update_xaxes(range=[0, max(upper * 1.1, 1)], title="Price per night", tickprefix="$")
    # Reversed category range with padding keeps A on top and its value label inside the plot.
    fig.update_yaxes(range=[1.6, -0.8], showgrid=False, title=None)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=20, t=30, b=10))
    return fig


def _card(row: pd.Series, role: str, color: str, filters) -> str:
    budget_on = filters.budget_usd is not None
    rows = [
        ("✓", f"Fits your ${filters.budget_usd:,.0f} budget" if budget_on else "Fits your budget",
         pct(row.within_budget_share, 0) if budget_on else "Set a budget"),
        ("⌂", "Places to choose from", number(row.listing_count)),
        ("★", "Have guest reviews", pct(row.reviewed_share, 0)),
        ("✎", "Typical number of reviews", number(row.median_total_reviews)),
        ("◷", "Open nights per year", number(row.median_available_nights)),
    ]
    body = "".join(f'<div class="cmp-row"><span><i>{icon}</i>{html.escape(label)}</span><b>{value}</b></div>'
                   for icon, label, value in rows)
    price_tip = (f"Median listed price per night across {number(row.price_n)} priced places "
                 f"({number(row.missing_price_n)} without a price are left out). Excludes taxes and fees.")
    range_text = (f"Most places {usd(row.price_p25)} – {usd(row.price_p75)}"
                  if pd.notna(row.price_p25) else "No prices available")
    return (
        f'<div class="cmp-card"><div class="cmp-head"><span class="cmp-badge" style="background:{color}">'
        f'{role}</span><div><div class="cmp-role">Neighborhood {role}</div>'
        f'<h3>{html.escape(str(row.neighbourhood))}</h3></div></div>'
        f'<div class="cmp-price"><b>{usd(row.median_price)}</b>night · typical{info(price_tip)}</div>'
        f'<div class="cmp-range">{range_text}{info("Middle half of prices: 25th to 75th percentile.")}</div>'
        f'{body}</div>'
    )


def _verdict(a: pd.Series, b: pd.Series, filters) -> str:
    # Price differences need 30+ priced places on both sides (display rule).
    if min(int(a.price_n), int(b.price_n)) < 30 or pd.isna(a.median_price) or pd.isna(b.median_price):
        return ("<b>Not enough priced places to compare prices here.</b>"
                "<small>Try another room type or wider filters.</small>")
    diff = float(a.median_price - b.median_price)
    cheaper, pricier = (a, b) if diff < 0 else (b, a)
    if abs(diff) < 1:
        headline = (f"<b>{html.escape(str(a.neighbourhood))}</b> and <b>{html.escape(str(b.neighbourhood))}</b> "
                    "have about the same typical price.")
    else:
        share = abs(diff) / float(pricier.median_price)
        headline = (f"<b>{html.escape(str(cheaper.neighbourhood))}</b> is typically <b>{usd(abs(diff))} cheaper</b> "
                    f"per night than {html.escape(str(pricier.neighbourhood))} ({share:.0%} less).")
    if filters.budget_usd is not None and pd.notna(a.within_budget_share) and pd.notna(b.within_budget_share):
        detail = (f"Within ${filters.budget_usd:,.0f}/night: {pct(a.within_budget_share, 0)} of places in "
                  f"{html.escape(str(a.neighbourhood))} vs {pct(b.within_budget_share, 0)} in "
                  f"{html.escape(str(b.neighbourhood))}.")
    else:
        detail = "Pick a nightly budget above to see how many places fit it."
    return f"{headline}<small>{detail}</small>"


def render_compare(frame: pd.DataFrame, filters) -> None:
    if frame.empty:
        st.info("No comparison is available under these filters.")
        return
    a, b = frame.iloc[0], frame.iloc[1]
    st.markdown(f'<div class="verdict">{_verdict(a, b, filters)}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    room = filters.room_types[0]
    for col, row, role, color in ((cols[0], a, "A", CORAL), (cols[1], b, "B", TEAL)):
        col.markdown(_card(row, role, color, filters), unsafe_allow_html=True)
        col.link_button(f"Search {row.neighbourhood} on Airbnb ↗",
                        airbnb_search(str(row.neighbourhood), room, filters.budget_usd), width="stretch")
    st.write("")
    with st.container(key="panel_compare_range"):
        panel_header("Price range", "Typical price and where most places fall",
                     "Dot = median price per night; bar = middle half of prices (25th–75th percentile). "
                     "Counted before the budget filter.")
        if pd.isna(a.median_price) and pd.isna(b.median_price):
            st.info("Neither neighborhood has prices under these filters.")
        else:
            st.plotly_chart(_range_chart(a, b), width="stretch", key="compare_range",
                            config={"displayModeBar": False})
