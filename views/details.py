from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

from phase2.clean_data import BOOLS
from .common import number, usd


DETAIL_COLUMNS = [
    "id", "neighbourhood", "room_type", "price", "minimum_nights", "number_of_reviews",
    "number_of_reviews_ltm", "last_review", "availability_365", "price_high_outlier",
    "price_under_10", "minimum_nights_missing", "review_fields_inconsistent",
    "review_counts_inconsistent", "coordinate_review",
]


def render_details(tables, filters, area: str | None, root: Path, file_hash: str) -> None:
    st.subheader("Listing evidence · selected snapshot listings")
    rows = tables["listings"].copy()
    if area is not None:
        rows = rows.loc[rows.neighbourhood.eq(area)]
    rows = rows[DETAIL_COLUMNS].copy()
    rows["airbnb_link"] = "https://www.airbnb.com/rooms/" + rows.id.astype("string")
    st.caption(f"Detail neighborhood: {area or 'All selected neighborhoods'} · {len(rows):,} listings. Global filters still apply; comparison filters do not change this detail population.")
    if rows.empty:
        st.info("No listings match this detail scope. Use Reset or clear the neighborhood selection.")

    control_cols = st.columns([2, 1, 1])
    sort_label = control_cols[0].selectbox(
        "Sort all filtered listings by", ["Listed price", "Total reviews", "Source last-12-month reviews"],
        key="detail_sort_field",
    )
    descending = control_cols[1].selectbox("Order", ["Ascending", "Descending"], key="detail_sort_order") == "Descending"
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
    st.caption(f"Showing page {page} of {pages}; sorted across all {len(rows):,} matching rows before the page slice. Null sort values are last. IDs are preserved as strings.")
    page_rows = rows.iloc[(int(page) - 1) * 50:int(page) * 50]
    st.dataframe(
        page_rows, hide_index=True, width="stretch", height=570,
        column_config={
            "id": st.column_config.TextColumn("Listing ID"),
            "price": st.column_config.NumberColumn("Listed USD/night", format="$%.0f"),
            "minimum_nights": st.column_config.NumberColumn("Minimum nights", format="%d"),
            "last_review": st.column_config.TextColumn("Last review (source date)"),
            "availability_365": st.column_config.NumberColumn("Source calendar availability (nights)", format="%d"),
            "airbnb_link": st.column_config.LinkColumn("Airbnb", display_text="Check current details"),
        },
    )
    csv_bytes = rows.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).encode("utf-8")
    st.download_button(
        f"Download all filtered listings ({len(rows):,} rows)", csv_bytes,
        file_name="la_traveler_filtered_listings.csv", mime="text/csv",
    )
    st.caption(
        f"Missing prices: {int(rows.price.isna().sum()):,} · unknown minimum stays: {int(rows.minimum_nights.isna().sum()):,}. "
        "Availability is the source calendar context, not a booking or occupancy measure."
    )

    st.subheader("Methods and data")
    manifest_path = root / "phase2" / "outputs" / "manifest.json"
    audit_path = root / "phase2" / "outputs" / "audit.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    st.write(f"Canonical CSV SHA-256: `{file_hash}`")
    st.write(f"Source SHA-256: `{manifest.get('source_sha256', 'not recorded')}`")
    st.write(f"Snapshot rows: {int(audit.get('output_rows', len(tables['listings']))):,}; source collection date: unknown.")
    st.write(f"High-price sensitivity threshold: >{usd(audit.get('high_price_threshold_usd'))}, defined as full-source Q3 + 3×IQR. Flagged records are retained unless the sensitivity toggle is on.")
    st.markdown(
        """**Metric rules.** Prices are observed listed USD/night, with unknown taxes, fees, discounts, and travel dates. No prices are imputed. Budget shares use pre-budget observed prices as the denominator. A specific trip length requires a known minimum stay no longer than the plan; “All stay lengths” also includes unknown minimum stays. Review counts are not ratings. Calendar availability is neither occupancy nor trip availability. Source last-12-month review counts and availability windows are source-relative, not today-relative. Small-sample bars require n≥30 as a display rule only."""
    )
    st.markdown("**Missing-data counts**")
    missing = audit.get("missing", {})
    if missing:
        st.dataframe(pd.DataFrame([{"field": key, "missing_rows": value} for key, value in missing.items()]), hide_index=True, width="stretch")
    st.markdown("**Source and attribution.** Inside Airbnb Los Angeles listings, CC BY 4.0. The exact snapshot date is not established by this local file.")
    contract_path = root / "phase2" / "DATA_CONTRACT.md"
    if contract_path.exists():
        contract = contract_path.read_text()
        st.download_button("Download data contract", contract, file_name="DATA_CONTRACT.md", mime="text/markdown")
        with st.expander("Read the complete data contract"):
            st.markdown(contract)
