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
    "airbnb_link", "neighbourhood", "room_type", "price", "minimum_nights", "number_of_reviews",
    "number_of_reviews_ltm", "last_review", "availability_365", "price_high_outlier", "id",
]


def render_details(tables, filters, area: str | None, root: Path, file_hash: str, detail_picker) -> None:
    section("Listings", "Places to check on Airbnb",
            "Every listing matching your filters, sorted across all pages. Links open the current Airbnb page; "
            "this snapshot does not confirm availability or today's price.")
    rows = tables["listings"].copy()
    if area is not None:
        rows = rows.loc[rows.neighbourhood.eq(area)]
    rows["airbnb_link"] = "https://www.airbnb.com/rooms/" + rows.id.astype("string")
    rows = rows[DETAIL_COLUMNS].copy()
    panel = st.container(key="panel_listings")
    control_cols = panel.columns([1.6, 1.6, 1, 1], vertical_alignment="bottom")
    with control_cols[0]:
        detail_picker()
    if rows.empty:
        panel.info("No listings match this focus and these filters. Choose “All selected neighborhoods”, widen the filters, or press Reset.")
    control_cols = control_cols[1:]
    sort_options = ["Price", "Most reviewed", "Reviews in past year"]
    sort_label = keep("detail_sort_field", control_cols[0].selectbox(
        "Sort by", sort_options, key="detail_sort_field",
        index=sort_options.index(kept("detail_sort_field", sort_options[0]))))
    order_options = ["Low to high", "High to low"]
    descending = keep("detail_sort_order", control_cols[1].selectbox(
        "Order", order_options, key="detail_sort_order",
        index=order_options.index(kept("detail_sort_order", order_options[0])))) == "High to low"
    sort_column = {
        "Price": "price",
        "Most reviewed": "number_of_reviews",
        "Reviews in past year": "number_of_reviews_ltm",
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
        "Page", min_value=1, max_value=pages, value=1, step=1,
        key=f"detail_page_{scope_sig}",
    )
    panel.caption(f"{len(rows):,} places · page {page} of {pages} · 50 per page")
    page_rows = rows.iloc[(int(page) - 1) * 50:int(page) * 50]
    panel.dataframe(
        page_rows, hide_index=True, width="stretch", height=570,
        column_config={
            "airbnb_link": st.column_config.LinkColumn("Airbnb", display_text="View listing ↗",
                                                       help="Opens the current Airbnb page for this listing."),
            "neighbourhood": st.column_config.TextColumn("Neighborhood"),
            "room_type": st.column_config.TextColumn("Room type"),
            "price": st.column_config.NumberColumn("Price/night", format="$%.0f",
                                                   help="Listed nightly price in the snapshot, before taxes and fees."),
            "minimum_nights": st.column_config.NumberColumn("Min. nights", format="%d"),
            "number_of_reviews": st.column_config.NumberColumn("Reviews", format="%d",
                                                               help="Total guest reviews. Not a rating."),
            "number_of_reviews_ltm": st.column_config.NumberColumn(
                "Reviews (past year)", format="%d", help="Reviews in the 12 months before the snapshot."),
            "last_review": st.column_config.TextColumn("Last review"),
            "availability_365": st.column_config.NumberColumn(
                "Open nights/yr", format="%d",
                help="Nights the host calendar showed open in the snapshot's next-year window. Not occupancy."),
            "price_high_outlier": st.column_config.CheckboxColumn(
                "Unusually high price", help="Above the market's outlier threshold (Q3 + 3×IQR)."),
            "id": st.column_config.TextColumn("Listing ID"),
        },
    )
    csv_bytes = rows.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).encode("utf-8")
    panel.download_button(
        f"Download all filtered listings ({len(rows):,} rows)", csv_bytes,
        file_name="la_traveler_filtered_listings.csv", mime="text/csv",
    )

    section("Methods", "How the numbers work")
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
        ("◎", "Neighborhoods", f"{tables['listings'].neighbourhood.nunique():,}", "Matching your filters"),
    ])
    cards = [
        ("Your real cost", "What you'll actually pay",
         "Prices here are the host's listed nightly rate. At checkout Airbnb adds a cleaning fee (often a flat "
         "amount per stay, so it matters more on short trips), its guest service fee, and local occupancy taxes. "
         "Hosts may also offer weekly or monthly discounts. Check the final total on Airbnb before booking."),
        ("Reviews", "What “reviews” means here",
         "We count how many guest reviews a place has. That shows people have stayed there, not how good it was: "
         "a place with 200 reviews could still be rated poorly. Open the listing to see its star rating."),
        ("Source", "Inside Airbnb · Los Angeles",
         "Listing snapshot, CC BY 4.0, from a single point in time, so prices and availability may have changed. "
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
