"""LA traveler comparison dashboard. Run with: streamlit run app.py"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import streamlit as st

from phase2.backend import Filters, compare_neighbourhoods, dashboard_data
from phase2.clean_data import load_listings
from views.compare import render_compare
from views.details import render_details
from views.explore import render_explore


ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "phase2" / "outputs" / "listings.csv"

st.set_page_config(page_title="LA Traveler Shortlist", page_icon="⌂", layout="wide")
st.markdown(
    """<style>
    .stApp { background: #fff; color: #17212b; }
    [data-testid="stMetric"] { background: #f6f8fa; border: 1px solid #e4e9ef;
      border-radius: .6rem; padding: .8rem 1rem; }
    [data-testid="stMetricLabel"] { color: #405164; }
    .stCaption { color: #526274; }
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading the canonical LA listings snapshot…")
def load_data(file_hash: str):
    # The content hash is an explicit cache key so replacing the canonical CSV
    # cannot leave stale listings in the UI.
    return load_listings(CANONICAL)


@st.cache_data(show_spinner=False)
def load_views(file_hash: str, filter_key: tuple):
    return dashboard_data(load_data(file_hash), Filters(*filter_key))


@st.cache_data(show_spinner=False)
def load_comparison(file_hash: str, filter_key: tuple, areas: tuple[str, str]):
    return compare_neighbourhoods(load_data(file_hash), Filters(*filter_key), areas)


def filter_key(filters: Filters) -> tuple:
    return (
        None if filters.neighbourhoods is None else tuple(sorted(filters.neighbourhoods)),
        None if filters.room_types is None else tuple(sorted(filters.room_types)),
        filters.trip_nights,
        filters.budget_usd,
        filters.min_reviews,
        filters.exclude_high_prices,
    )


def reset_dashboard() -> None:
    # Clearing widget state also clears saved Plotly/table selections, so a
    # stale chart event cannot restore a detail scope after Reset.
    st.session_state.clear()


def set_detail(area: str | None) -> None:
    st.session_state.detail_neighbourhood = area


if not CANONICAL.exists():
    st.error(f"Canonical Phase 2 data is missing: {CANONICAL}")
    st.info("From the project folder, build it with `python -m phase2.build`.")
    st.stop()

file_hash = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
if st.session_state.get("canonical_file_hash") != file_hash:
    load_data.clear()
    load_views.clear()
    load_comparison.clear()
    st.session_state.canonical_file_hash = file_hash
listings = load_data(file_hash)
neighbourhoods = sorted(listings.neighbourhood.dropna().unique().tolist())
room_types = sorted(listings.room_type.dropna().unique().tolist())
default_room = "Entire home/apt" if "Entire home/apt" in room_types else room_types[0]
default_a = "Hollywood" if "Hollywood" in neighbourhoods else neighbourhoods[0]
default_b = "Venice" if "Venice" in neighbourhoods else neighbourhoods[min(1, len(neighbourhoods) - 1)]

# Keep the keyboard selector synchronized with chart/table selection before
# constructing the widget. Its callback writes the same authoritative state.
detail = st.session_state.get("detail_neighbourhood")
if st.session_state.get("detail_selector") != detail:
    st.session_state["detail_selector"] = detail

st.title("Find your Los Angeles shortlist")
st.caption(
    "Los Angeles listing snapshot; collection date unknown; prices and availability may have changed."
)

with st.sidebar:
    st.header("Explore filters")
    st.button("Reset", on_click=reset_dashboard, use_container_width=True)
    selected_areas = st.multiselect(
        "Neighborhoods", neighbourhoods, default=neighbourhoods, key="filter_neighbourhoods"
    )
    selected_rooms = st.multiselect(
        "Room types", room_types, default=[default_room], key="filter_room_types"
    )
    all_stays = st.checkbox("All stay lengths", key="all_stay_lengths")
    nights = st.number_input(
        "Planned nights", min_value=1, max_value=365, value=7, step=1,
        disabled=all_stays, key="planned_nights",
    )
    has_budget = st.checkbox("Set a nightly budget", key="budget_enabled")
    budget = st.number_input(
        "Nightly budget (USD)", min_value=0.01, value=250.0, step=10.0,
        disabled=not has_budget, key="budget_usd",
    )
    min_reviews = st.number_input(
        "Minimum total reviews", min_value=0, value=0, step=1, key="minimum_reviews"
    )
    exclude_high = st.checkbox("Exclude flagged high prices", key="exclude_high_prices")
    st.caption(
        "A specific stay length excludes unknown minimum stays. Compatibility does not confirm booking eligibility."
    )
    st.markdown("---")
    st.subheader("Detail scope")
    st.selectbox(
        "Neighborhood (keyboard accessible)",
        [None, *neighbourhoods],
        format_func=lambda value: "All selected neighborhoods" if value is None else value,
        key="detail_selector",
        on_change=lambda: set_detail(st.session_state.detail_selector),
    )
    st.caption("Chart, table, and keyboard selection share this detail scope.")

filters = Filters(
    tuple(selected_areas),
    tuple(selected_rooms),
    None if all_stays else int(nights),
    float(budget) if has_budget else None,
    int(min_reviews),
    bool(exclude_high),
)
tables = load_views(file_hash, filter_key(filters))

st.caption(
    "Active filters: "
    f"{len(selected_areas):,} neighborhoods · {', '.join(selected_rooms) if selected_rooms else 'no room types'} · "
    f"{'all stay lengths' if filters.trip_nights is None else f'{filters.trip_nights} planned nights'} · "
    f"{'no budget' if filters.budget_usd is None else f'${filters.budget_usd:,.2f}/night'} · "
    f"minimum {filters.min_reviews} total reviews · "
    f"{'high prices excluded' if filters.exclude_high_prices else 'high-price sensitivity off'}"
)

explore_tab, compare_tab, details_tab = st.tabs(
    ["Explore", "Compare neighborhoods", "Listing details & methods"]
)

with explore_tab:
    room_views = {
        room: load_views(file_hash, filter_key(replace(filters, room_types=(room,))))
        for room in filters.room_types or ()
    }
    render_explore(tables, filters, set_detail, room_views)

with compare_tab:
    st.caption(
        "Comparison ignores Explore neighborhood and room selections. It uses one room type and inherits stay length, budget, review, and sensitivity filters."
    )
    cols = st.columns(3)
    a = cols[0].selectbox("Comparison A", neighbourhoods,
                           index=neighbourhoods.index(default_a), key="compare_neighbourhood_a")
    b = cols[1].selectbox("Reference B", neighbourhoods,
                           index=neighbourhoods.index(default_b), key="compare_neighbourhood_b")
    comparison_room = cols[2].selectbox(
        "Comparison room type", room_types, index=room_types.index(default_room), key="compare_room_type"
    )
    if a == b:
        st.warning("Choose two distinct neighborhoods to compare.")
    else:
        comparison_filters = replace(filters, neighbourhoods=None, room_types=(comparison_room,))
        comparison_data = load_comparison(
            file_hash, filter_key(comparison_filters), (a, b)
        )
        render_compare(comparison_data, comparison_filters)

with details_tab:
    render_details(tables, filters, st.session_state.get("detail_neighbourhood"), ROOT, file_hash)
