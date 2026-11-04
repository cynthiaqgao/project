from __future__ import annotations

import csv
import hashlib
import html
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

from phase2.clean_data import BOOLS
from .common import keep, kept, number, section, stat_cards, usd


DETAIL_COLUMNS = [
    "id", "neighbourhood", "room_type", "price", "minimum_nights", "number_of_reviews",
    "number_of_reviews_ltm", "last_review", "availability_365", "price_high_outlier",
    "price_under_10", "minimum_nights_missing", "review_fields_inconsistent",
    "review_counts_inconsistent", "coordinate_review",
]


def render_details(tables, filters, area: str | None, root: Path, file_hash: str, detail_picker) -> None:
    section("03 / Listings", "Listings to check on Airbnb",
            "Every filtered listing, sorted before paging. Links open current details; nothing here confirms availability.")
    rows = tables["listings"].copy()
    if area is not None:
        rows = rows.loc[rows.neighbourhood.eq(area)]
    rows = rows[DETAIL_COLUMNS].copy()
    rows["airbnb_link"] = "https://www.airbnb.com/rooms/" + rows.id.astype("string")
    panel = st.container(key="panel_listings")
    control_cols = panel.columns([1.6, 1.6, 1, 1], vertical_alignment="bottom")
    with control_cols[0]:
        detail_picker()
    panel.caption(f"Focus: {area or 'All selected neighborhoods'} · {len(rows):,} listings. The filter bar still applies; "
                  "comparison choices do not change this list.")
    if rows.empty:
        panel.info("No listings match this focus and these filters. Choose “All selected neighborhoods”, widen the filters, or press Reset.")
    control_cols = control_cols[1:]
    sort_options = ["Listed price", "Total reviews", "Source last-12-month reviews"]
    sort_label = keep("detail_sort_field", control_cols[0].selectbox(
        "Sort by", sort_options, key="detail_sort_field",
        index=sort_options.index(kept("detail_sort_field", sort_options[0]))))
    order_options = ["Ascending", "Descending"]
    descending = keep("detail_sort_order", control_cols[1].selectbox(
        "Order", order_options, key="detail_sort_order",
        index=order_options.index(kept("detail_sort_order", order_options[0])))) == "Descending"
    sort_column = {
        "Listed price": "price",
        "Total reviews": "number_of_reviews",
        "Source last-12-month reviews": "number_of_reviews_ltm",
    }[sort_label]
    # Sort the whole detail scope before pagination; IDs remain string tie-breakers.
    rows = rows.sort_values(
        [sort_column, "id"], ascending=[not descending, True], na_position="last", kind="mergesort"
    ).reset_index(drop=True)
    scope_sig = hashlib.sha256(
        repr((file_hash, area, filters.neighbourhoods, filters.room_types, filters.trip_nights,
              filters.budget_usd, filters.min_reviews, filters.exclude_high_prices,
              sort_column, descending)).encode()
    ).hexdigest()[:12]
    pages = max(1, math.ceil(len(rows) / 50))
    page = control_cols[2].number_input(
        "Page (50 rows)", min_value=1, max_value=pages, value=1, step=1,
        key=f"detail_page_{scope_sig}",
    )
    panel.caption(f"Showing page {page} of {pages}; sorted across all {len(rows):,} matching rows before the page slice. Null sort values are last. IDs are preserved as strings.")
    page_rows = rows.iloc[(int(page) - 1) * 50:int(page) * 50]
    panel.dataframe(
        page_rows, hide_index=True, width="stretch", height=570,
        column_config={
            "id": st.column_config.TextColumn("Listing ID"),
            "neighbourhood": st.column_config.TextColumn("Neighborhood"),
            "room_type": st.column_config.TextColumn("Room type"),
            "number_of_reviews": st.column_config.NumberColumn("Total reviews", format="%d"),
            "number_of_reviews_ltm": st.column_config.NumberColumn("Source last-12-month reviews", format="%d"),
            "price": st.column_config.NumberColumn("Listed USD/night", format="$%.0f"),
            "minimum_nights": st.column_config.NumberColumn("Minimum nights", format="%d"),
            "last_review": st.column_config.TextColumn("Last review (source date)"),
            "availability_365": st.column_config.NumberColumn("Source calendar availability (nights)", format="%d"),
            "airbnb_link": st.column_config.LinkColumn("Airbnb", display_text="Check current details"),
        },
    )
    csv_bytes = rows.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).encode("utf-8")
    panel.download_button(
        f"Download all filtered listings ({len(rows):,} rows)", csv_bytes,
        file_name="la_traveler_filtered_listings.csv", mime="text/csv",
    )
    panel.caption(
        f"Missing prices: {int(rows.price.isna().sum()):,} · unknown minimum stays: {int(rows.minimum_nights.isna().sum()):,}. "
        "Availability is the source calendar context, not a booking or occupancy measure."
    )

    section("04 / Methods", "Data and methods", "How every number on this dashboard is calculated.")
    manifest_path = root / "phase2" / "outputs" / "manifest.json"
    audit_path = root / "phase2" / "outputs" / "audit.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    snapshot_rows = int(audit.get("output_rows", len(tables["listings"])))
    missing = audit.get("missing", {})
    stat_cards([
        ("⌂", "Snapshot listings", f"{snapshot_rows:,}", "One row per listing ID"),
        ("$", "Missing prices", number(missing.get("price")), "Kept, never imputed"),
        ("!", "High-price threshold", f">{usd(audit.get('high_price_threshold_usd'))}", "Q3 + 3×IQR; flagged, kept"),
        ("?", "Collection date", "Unknown", "Not a live search or quote"),
    ])
    cards = [
        ("Source", "Inside Airbnb · Los Angeles",
         "Listing snapshot, CC BY 4.0. The exact collection date is not established by the supplied file. "
         f"Source SHA-256 <code>{html.escape(str(manifest.get('source_sha256', 'not recorded')))}</code>; "
         f"canonical CSV <code>{html.escape(file_hash)}</code>."),
        ("Prices", "Listed USD per night",
         "Observed listed prices only, excluding unknown taxes, fees and discounts. Not a dated quote or total trip "
         "cost. Medians and middle-50% ranges are recomputed from listing rows; no prices are imputed."),
        ("Budget", "Pre-budget denominators",
         "Budget share = observed prices at or below the budget ÷ all observed prices before the budget filter, so "
         "a budget can never force the share to 100%."),
        ("Stay length", "Minimum-night compatibility",
         "A listing qualifies when its minimum nights are no more than the planned stay. Unknown minimums are "
         "excluded unless “Any stay length” is chosen. This is not proof of booking eligibility."),
        ("Reviews", "History, not ratings",
         "Review counts are not ratings, quality or safety scores. Last-12-month counts and calendar availability "
         "are source-relative windows, not today-relative, and availability is not occupancy."),
        ("Display rules", "Small samples stay visible",
         "Ranked bars require 30+ observed values for their metric. This is a display rule, not statistical "
         "significance; small groups remain in the map, table and comparison with warnings."),
    ]
    st.markdown(
        '<div class="method-grid">' + "".join(
            f'<div class="method-card"><span>{html.escape(kicker.upper())}</span><h3>{html.escape(title)}</h3>'
            f'<p>{body}</p></div>' for kicker, title, body in cards) + "</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    with st.expander("Missing-data counts by field"):
        if missing:
            st.dataframe(pd.DataFrame([{"field": key, "missing_rows": value} for key, value in missing.items()]),
                         hide_index=True, width="stretch")
    contract_path = root / "phase2" / "DATA_CONTRACT.md"
    if contract_path.exists():
        contract = contract_path.read_text()
        with st.expander("Read the complete data contract"):
            st.markdown(contract)
        st.download_button("Download data contract", contract, file_name="DATA_CONTRACT.md", mime="text/markdown")
