from __future__ import annotations

import pandas as pd
import streamlit as st

from .common import add_small_metric_flags, number, pct, usd


def render_compare(frame: pd.DataFrame, filters) -> None:
    if frame.empty:
        st.info("No comparison rows are available under the selected filters.")
        return
    a, b = frame.iloc[0], frame.iloc[1]
    st.subheader(f"Like-for-like evidence · {filters.room_types[0]} · pre-budget population")
    cols = st.columns(2)
    for column, row, role in zip(cols, (a, b), ("Comparison A", "Reference B")):
        with column:
            st.markdown(f"#### {role}: {row.neighbourhood}")
            st.metric("Median listed nightly price", usd(row.median_price))
            st.caption(f"Middle 50% price range: {usd(row.price_p25)}–{usd(row.price_p75)} · price_n={number(row.price_n)} · missing prices={number(row.missing_price_n)}")
            st.metric("Within-budget share", pct(row.within_budget_share) if filters.budget_usd is not None else "Set a budget")
            st.caption(
                f"Pre-budget numerator/denominator: {number(row.within_budget_n)} / {number(row.price_n)} observed prices"
                if filters.budget_usd is not None
                else f"Budget not set; {number(row.price_n)} observed prices define the pre-budget population."
            )
            st.write(f"Matching listings: {number(row.listing_count)} · reviewed-listing share: {pct(row.reviewed_share)}")
            st.write(f"Median total reviews: {number(row.median_total_reviews)} (n={number(row.review_n)})")
            st.write(f"Median source last-12-month reviews: {number(row.median_reviews_ltm)} (n={number(row.review_ltm_n)})")
            st.write(f"Median source availability: {number(row.median_available_nights)} nights (n={number(row.availability_n)})")

    threshold = min(int(a.price_n), int(b.price_n)) >= 30
    if threshold:
        st.subheader("Differences · A minus B")
        deltas = st.columns(3)
        if pd.notna(a.median_price) and pd.notna(b.median_price):
            deltas[0].metric("Median price difference", usd(a.median_price - b.median_price))
            if b.median_price > 0:
                deltas[1].metric("Relative median price difference", pct(a.median_price / b.median_price - 1))
            else:
                deltas[1].metric("Relative median price difference", "N/A")
        else:
            deltas[0].metric("Median price difference", "N/A")
        if filters.budget_usd is not None and pd.notna(a.within_budget_share) and pd.notna(b.within_budget_share):
            deltas[2].metric("Within-budget share difference", f"{100 * (a.within_budget_share - b.within_budget_share):.1f} pp")
        else:
            deltas[2].metric("Within-budget share difference", "Set a budget" if filters.budget_usd is None else "N/A")
    else:
        st.warning("At least one neighborhood has price_n<30. No numeric price winner or difference is shown; this is a display rule, not statistical significance.")
    st.caption("The comparison uses the same room type and inherited trip/review/sensitivity filters for both neighborhoods. Budget affordability uses the full pre-budget priced population.")
    st.dataframe(add_small_metric_flags(frame), hide_index=True, width="stretch")
