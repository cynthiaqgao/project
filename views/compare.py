from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .common import (CORAL, INK, TEAL, add_small_metric_flags, number, panel_header, pct, section,
                     stat_cards, style_fig, table_formats, usd)


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
            hovertemplate=(f"<b>{html.escape(str(row.neighbourhood))}</b><br>Median ${row.median_price:,.0f}/night"
                           f"<br>Middle 50%: ${row.price_p25:,.0f}–${row.price_p75:,.0f}"
                           f"<br>price_n {int(row.price_n):,}<extra></extra>"),
        ))
    upper = max(float(a.price_p75) if pd.notna(a.price_p75) else 0, float(b.price_p75) if pd.notna(b.price_p75) else 0)
    style_fig(fig, height=230)
    fig.update_xaxes(range=[0, max(upper * 1.1, 1)], title="Listed price (USD/night)", tickprefix="$")
    # Reversed category range with padding keeps A on top and its value label inside the plot.
    fig.update_yaxes(range=[1.6, -0.8], showgrid=False, title=None)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=20, t=30, b=10))
    return fig


def render_compare(frame: pd.DataFrame, filters) -> None:
    if frame.empty:
        st.info("No comparison rows are available under the selected filters.")
        return
    a, b = frame.iloc[0], frame.iloc[1]
    budget_on = filters.budget_usd is not None
    cols = st.columns(2)
    for column, row, role, color in zip(cols, (a, b), ("Comparison A", "Reference B"), (CORAL, TEAL)):
        with column, st.container(key=f"panel_compare_{role[-1]}"):
            st.markdown(
                f'<div class="room-chip"><i style="background:{color}"></i>{role} · '
                f'{html.escape(str(row.neighbourhood))}</div>',
                unsafe_allow_html=True,
            )
            stat_cards([
                ("$", "Median nightly price", usd(row.median_price),
                 f"Middle 50%: {usd(row.price_p25)}–{usd(row.price_p75)} · price_n={number(row.price_n)}"),
                ("✓", "Within budget", pct(row.within_budget_share) if budget_on else "Set a budget",
                 f"{number(row.within_budget_n)} of {number(row.price_n)} priced · pre-budget" if budget_on
                 else "Choose a nightly budget above"),
            ])
            st.markdown(
                f"**{number(row.listing_count)}** matching listings · {number(row.missing_price_n)} missing prices  \n"
                f"Reviewed listings: **{pct(row.reviewed_share)}**  \n"
                f"Median total reviews: **{number(row.median_total_reviews)}** (n={number(row.review_n)})  \n"
                f"Median source last-12-month reviews: **{number(row.median_reviews_ltm)}** (n={number(row.review_ltm_n)})  \n"
                f"Median source calendar availability: **{number(row.median_available_nights)} nights** (n={number(row.availability_n)})"
            )

    with st.container(key="panel_compare_range"):
        panel_header("Price spread · pre-budget population", "Typical price and middle 50% range",
                     "Dot = median listed USD/night; bar = 25th–75th percentile. Same room type and filters for both.")
        if pd.isna(a.median_price) and pd.isna(b.median_price):
            st.info("Neither neighborhood has observed prices under these filters.")
        else:
            st.plotly_chart(_range_chart(a, b), width="stretch", key="compare_range", config={"displayModeBar": False})

    section("A minus B", "Differences", "A is the comparison; B is the reference.")
    if min(int(a.price_n), int(b.price_n)) >= 30:
        price_delta = (usd(a.median_price - b.median_price)
                       if pd.notna(a.median_price) and pd.notna(b.median_price) else "N/A")
        relative = (pct(a.median_price / b.median_price - 1)
                    if pd.notna(a.median_price) and pd.notna(b.median_price) and b.median_price > 0 else "N/A")
        if budget_on and pd.notna(a.within_budget_share) and pd.notna(b.within_budget_share):
            share_delta = f"{100 * (a.within_budget_share - b.within_budget_share):+.1f} pp"
        else:
            share_delta = "Set a budget" if not budget_on else "N/A"
        stat_cards([
            ("$", "Median price difference", price_delta, "A − B, listed USD/night"),
            ("%", "Relative price difference", relative, "A ÷ B − 1"),
            ("✓", "Budget share difference", share_delta, "Percentage points, pre-budget"),
            ("★", "Reviewed share difference",
             f"{100 * (a.reviewed_share - b.reviewed_share):+.1f} pp"
             if pd.notna(a.reviewed_share) and pd.notna(b.reviewed_share) else "N/A",
             "Percentage points"),
        ])
    else:
        st.warning("At least one neighborhood has fewer than 30 observed prices, so no numeric price difference "
                   "or winner is shown. This is a display rule, not statistical significance.")
    with st.expander("Comparison table"):
        table = add_small_metric_flags(frame)
        st.dataframe(table.style.format(table_formats(table), na_rep="N/A"), hide_index=True, width="stretch")
