"""LA traveler comparison dashboard. Run with: streamlit run app.py"""
from __future__ import annotations

import hashlib
import html
from dataclasses import replace
from pathlib import Path

import streamlit as st

from phase2.backend import Filters, compare_neighbourhoods, dashboard_data
from phase2.clean_data import load_listings
from views.common import keep, kept, number, section
from views.compare import render_compare
from views.details import render_details
from views.explore import render_explore


ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "phase2" / "outputs" / "listings.csv"
ALL_ROOMS = "All room types (shown separately)"
BUDGET_STEPS = [*range(50, 1001, 25), None]
REVIEW_OPTIONS = [0, 1, 5, 10, 25, 50, 100]
PAGES = ["Explore", "Compare neighborhoods", "Listings & methods"]
PAGE_ICONS = {"Explore": "◎", "Compare neighborhoods": "⇄", "Listings & methods": "☰"}

st.set_page_config(page_title="LA Stay Shortlist", page_icon="⌂", layout="wide")
st.markdown(f"<style>{(ROOT / 'views' / 'style.css').read_text()}</style>", unsafe_allow_html=True)


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
    # stale chart event cannot restore a detail scope after Reset. The current
    # page is kept so Reset does not navigate away.
    page = st.session_state.get("nav", PAGES[0])
    st.session_state.clear()
    st.session_state.nav = page


def set_detail(area: str | None) -> None:
    st.session_state.detail_neighbourhood = area


def detail_picker(neighbourhoods: list[str]) -> None:
    st.selectbox(
        "Focus neighborhood (keyboard accessible)",
        [None, *neighbourhoods],
        format_func=lambda value: "All selected neighborhoods" if value is None else value,
        key="detail_selector",
        on_change=lambda: set_detail(st.session_state.detail_selector),
        help="Chart clicks, table row selection and this dropdown share one detail scope.",
    )


def stay_label(nights: int | None) -> str:
    if nights is None:
        return "Any stay length"
    named = {7: " · 1 week", 14: " · 2 weeks", 28: " · 4 weeks", 30: " · 1 month", 365: " · 1 year"}
    return f"{nights} night{'s' if nights != 1 else ''}{named.get(nights, '')}"


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

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">⌂</span>'
        '<span class="brand-name">LA STAY<b>SHORTLIST</b></span></div>'
        '<div class="brand-caption">TRAVELER DASHBOARD · DSO 576</div>',
        unsafe_allow_html=True,
    )
    page = st.radio("Page", PAGES, key="nav", label_visibility="collapsed",
                    format_func=lambda name: f"{PAGE_ICONS[name]}   {name}")
    st.write("")
    st.button("↺  Reset all filters", on_click=reset_dashboard, width="stretch")
    st.markdown(
        f'<div class="sidebar-foot"><span class="live-dot"></span>Listing snapshot'
        f'<small>{len(listings):,} Los Angeles listings · Inside Airbnb</small></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="headline-row"><div>'
    '<div class="eyebrow">Los Angeles stay planner</div>'
    '<h1>Find your Los Angeles <em>shortlist</em>.</h1>'
    '<p class="subtitle">Compare neighborhoods by listed nightly price, budget fit and review history, '
    'then check live prices and availability on Airbnb.</p>'
    f'</div><div class="snapshot-badge"><strong>{len(listings):,}</strong><small>LISTINGS IN SNAPSHOT</small></div></div>',
    unsafe_allow_html=True,
)

with st.container(key="filter_bar"):
    top = st.columns(3, vertical_alignment="bottom")
    selected_areas = top[0].multiselect(
        "Neighborhoods", neighbourhoods, key="filter_neighbourhoods", placeholder="All neighborhoods",
        help="Leave empty to search every neighborhood.",
    )
    room_choice = top[1].selectbox(
        "Room type", [*room_types, ALL_ROOMS], index=room_types.index(default_room), key="filter_room_type",
        help="Type of space, not number of bedrooms.",
    )
    # Default 7 nights is seeded via session state; a widget default of None is
    # what lets travelers clear the box for "any stay length".
    st.session_state.setdefault("filter_stay", 7)
    nights = top[2].number_input(
        "Stay length (nights)", min_value=1, max_value=365, value=None, step=1, key="filter_stay",
        placeholder="Any stay length",
        help="Shows places whose minimum stay fits your trip. Clear the box for any stay length, "
             "which also includes places with an unknown minimum stay.",
    )
    nights = None if nights is None else int(nights)
    bottom = st.columns(3, vertical_alignment="bottom")
    budget = bottom[0].select_slider(
        "Nightly budget", BUDGET_STEPS, value=None, key="filter_budget",
        format_func=lambda v: "No limit" if v is None else f"${v:,}",
        help="Listed nightly price before taxes and fees. Slide all the way right for no limit.",
    )
    min_reviews = bottom[1].selectbox(
        "Reviews", REVIEW_OPTIONS, format_func=lambda n: "Any" if n == 0 else f"{n}+ reviews",
        key="filter_min_reviews", help="Minimum number of guest reviews.",
    )
    exclude_high = bottom[2].toggle(
        "Hide unusually high prices", key="exclude_high_prices",
        help="Hides listings priced above the market's outlier threshold (Q3 + 3×IQR).",
    )

filters = Filters(
    tuple(selected_areas) if selected_areas else None,
    tuple(room_types) if room_choice == ALL_ROOMS else (room_choice,),
    nights,
    float(budget) if budget is not None else None,
    int(min_reviews),
    bool(exclude_high),
)
tables = load_views(file_hash, filter_key(filters))

area_text = "all neighborhoods" if not selected_areas else (
    selected_areas[0] if len(selected_areas) == 1 else f"{len(selected_areas)} neighborhoods")
st.markdown(
    '<div class="filter-summary">Showing '
    f'<b>{number(len(tables["listings"]))}</b> listings · {html.escape(area_text)} · '
    f'{html.escape(room_choice if room_choice != ALL_ROOMS else "all room types")} · '
    f'{html.escape(stay_label(filters.trip_nights).lower())} · '
    f'{"no budget" if filters.budget_usd is None else f"budget ${filters.budget_usd:,.0f}/night"} · '
    f'{"any reviews" if not filters.min_reviews else f"{filters.min_reviews}+ reviews"} · '
    f'{"high prices hidden" if filters.exclude_high_prices else "all prices"}</div>',
    unsafe_allow_html=True,
)

if page == "Explore":
    room_views = {
        room: load_views(file_hash, filter_key(replace(filters, room_types=(room,))))
        for room in filters.room_types or ()
    }
    render_explore(tables, filters, set_detail, room_views, lambda: detail_picker(neighbourhoods))

elif page == "Compare neighborhoods":
    section("Compare", "Two neighborhoods, side by side",
            "Both use the same room type plus your stay length, budget, review and price filters. "
            "The neighborhood filter above is ignored here.")
    with st.container(key="panel_compare_controls"):
        cols = st.columns(3)
        a = keep("compare_neighbourhood_a", cols[0].selectbox(
            "Neighborhood A", neighbourhoods, key="compare_neighbourhood_a",
            index=neighbourhoods.index(kept("compare_neighbourhood_a", default_a))))
        b = keep("compare_neighbourhood_b", cols[1].selectbox(
            "Neighborhood B", neighbourhoods, key="compare_neighbourhood_b",
            index=neighbourhoods.index(kept("compare_neighbourhood_b", default_b))))
        comparison_room = keep("compare_room_type", cols[2].selectbox(
            "Room type", room_types, key="compare_room_type",
            index=room_types.index(kept("compare_room_type", default_room))))
    if a == b:
        st.warning("Choose two different neighborhoods to compare.")
    else:
        comparison_filters = replace(filters, neighbourhoods=None, room_types=(comparison_room,))
        comparison_data = load_comparison(file_hash, filter_key(comparison_filters), (a, b))
        render_compare(comparison_data, comparison_filters)

else:
    render_details(tables, filters, st.session_state.get("detail_neighbourhood"), ROOT, file_hash,
                   lambda: detail_picker(neighbourhoods))

st.markdown(
    '<div class="app-footer"><span>Source · Inside Airbnb Los Angeles listings · CC BY 4.0</span>'
    '<span>Listed prices are not quotes · Reviews are not ratings</span></div>',
    unsafe_allow_html=True,
)
