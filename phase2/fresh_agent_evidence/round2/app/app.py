"""LA Airbnb Traveler Comparison Dashboard (Phase 3 MVP).

Run from the repository root:  streamlit run app.py
Renders controls and coordinates state; all metrics come from phase2.backend.
"""
import json
import time
from dataclasses import astuple, replace
from pathlib import Path

import streamlit as st

from phase2.backend import Filters, dashboard_data, compare_neighbourhoods
from phase2.clean_data import ROOMS, fingerprint, load_listings
from views.common import SNAPSHOT_NOTE, describe_filters
from views.compare import render_compare, render_compare_controls
from views.details import render_listings, render_methods
from views.explore import render_explore

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / 'phase2' / 'outputs' / 'listings.csv'
AUDIT = ROOT / 'phase2' / 'outputs' / 'audit.json'
CONTRACT = 'phase2/DATA_CONTRACT.md'
ALL_SCOPE = 'All neighborhoods (global scope)'
DEFAULT_ROOM = 'Entire home/apt'
DEFAULT_NIGHTS = 7


# ------------------------------------------------------------------ cached data access
@st.cache_data(show_spinner='Loading canonical listings…', max_entries=2)
def load_canonical(sha256):
    """Cached by canonical file SHA-256; a new hash yields a new cache entry."""
    return load_listings(CANONICAL)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_views(sha256, filter_key):
    return dashboard_data(load_canonical(sha256), Filters(*filter_key))


@st.cache_data(show_spinner=False, max_entries=64)
def cached_compare(sha256, filter_key, areas):
    return compare_neighbourhoods(load_canonical(sha256), Filters(*filter_key), areas)


@st.cache_data(show_spinner=False)
def read_audit(sha256):
    try:
        return json.loads(AUDIT.read_text())
    except (OSError, ValueError):
        return {}


def normalized_key(filters):
    """Hashable, order-independent Filters tuple for the aggregation cache."""
    f = replace(filters,
                neighbourhoods=None if filters.neighbourhoods is None else tuple(sorted(filters.neighbourhoods)),
                room_types=None if filters.room_types is None else tuple(sorted(filters.room_types)))
    return astuple(f)


# ------------------------------------------------------------------ state
def set_defaults(neighbourhoods):
    st.session_state['f_neighbourhoods'] = list(neighbourhoods)
    st.session_state['f_rooms'] = [DEFAULT_ROOM]
    st.session_state['f_all_stays'] = False
    st.session_state['f_nights'] = DEFAULT_NIGHTS
    st.session_state['f_budget'] = None
    st.session_state['f_min_reviews'] = 0
    st.session_state['f_exclude_high'] = False
    st.session_state['detail_area'] = ALL_SCOPE
    for key in ['listing_page', 'segment_search', 'map_metric', 'map_mode', 'cdf_log_x',
                'compare_a', 'compare_b', 'compare_room']:
        st.session_state.pop(key, None)


def set_detail(area):
    """Explicit selection callback for map/table clicks; never touches global filters."""
    st.session_state['detail_area'] = area if area else ALL_SCOPE
    st.session_state.pop('listing_page', None)


def sidebar_filters(neighbourhoods, room_options):
    sb = st.sidebar
    sb.header('Filters (apply to Explore)')
    sb.button('Reset to defaults', on_click=set_defaults, args=(neighbourhoods,), key='reset_sidebar',
              use_container_width=True)
    chosen = sb.multiselect('Neighborhoods (clear all = no results)', neighbourhoods, key='f_neighbourhoods')
    rooms = sb.multiselect('Room types (not bedrooms)', room_options, key='f_rooms')
    all_stays = sb.checkbox('All stay lengths (includes unknown minimum stays)', key='f_all_stays')
    nights = sb.number_input('Planned nights (1–365)', min_value=1, max_value=365, step=1, key='f_nights',
                             disabled=all_stays,
                             help='Listings qualify when their minimum nights ≤ planned nights. '
                                  'Unknown minimum stays are excluded.')
    budget = sb.number_input('Nightly budget, USD (optional)', min_value=0.01, step=10.0, key='f_budget',
                             placeholder='No budget', help='Leave empty for no budget.')
    min_reviews = sb.number_input('Minimum total reviews', min_value=0, step=1, key='f_min_reviews')
    exclude = sb.toggle('Exclude flagged high prices', key='f_exclude_high',
                        help='Excludes listings above the fixed full-source high-price threshold.')
    nb = None if set(chosen) == set(neighbourhoods) else tuple(chosen)
    rt = None if set(rooms) == set(room_options) else tuple(rooms)
    return Filters(neighbourhoods=nb, room_types=rt, trip_nights=None if all_stays else int(nights),
                   budget_usd=None if budget is None else float(budget), min_reviews=int(min_reviews),
                   exclude_high_prices=bool(exclude))


# ------------------------------------------------------------------ app
def main():
    st.set_page_config(page_title='LA Airbnb Traveler Comparison', layout='wide')
    st.markdown('<style>.stApp{background:#FFFFFF;color:#1F2328}</style>', unsafe_allow_html=True)
    started = time.perf_counter()
    sha = fingerprint(CANONICAL)
    if st.session_state.get('_canonical_sha') not in (None, sha):
        st.cache_data.clear()  # canonical data changed: drop stale loads/aggregations
    st.session_state['_canonical_sha'] = sha
    listings = load_canonical(sha)
    neighbourhoods = sorted(listings.neighbourhood.dropna().unique().tolist())
    room_options = [r for r in ROOMS if r in set(listings.room_type)] + sorted(
        set(listings.room_type) - set(ROOMS))
    if 'f_rooms' not in st.session_state:
        set_defaults(neighbourhoods)

    filters = sidebar_filters(neighbourhoods, room_options)
    data = cached_views(sha, normalized_key(filters))
    panel_rooms = list(filters.room_types) if filters.room_types is not None else room_options
    panel_rooms = [r for r in room_options if r in panel_rooms]

    detail_options = [ALL_SCOPE] + sorted(data['segments'].neighbourhood.unique().tolist())
    if st.session_state.get('detail_area') not in detail_options:
        st.session_state['detail_area'] = ALL_SCOPE
    st.sidebar.header('Detail selection')
    st.sidebar.selectbox('Detail neighborhood (same as clicking a map marker or table row)', detail_options,
                         key='detail_area')
    st.sidebar.caption('Detail selection changes only the listing-detail scope, never the filters above.')
    detail_area = None if st.session_state['detail_area'] == ALL_SCOPE else st.session_state['detail_area']

    st.title('LA Airbnb Traveler Comparison Dashboard')
    st.info(SNAPSHOT_NOTE)
    filter_text = describe_filters(filters, len(neighbourhoods))
    st.caption('Active filters — ' + ' · '.join(f'{k}: {v}' for k, v in filter_text.items()) +
               (f' · Detail: {detail_area}' if detail_area else ''))
    if int(data['overview'].listing_count.iloc[0]) == 0:
        st.error('No listings match these filters')
        st.button('Reset', on_click=set_defaults, args=(neighbourhoods,), key='reset_empty')

    explore, compare, details = st.tabs(['Explore', 'Compare neighborhoods', 'Listing details & methods'])
    with explore:
        render_explore(data, filters, panel_rooms, detail_area, set_detail)
    with compare:
        area_a, area_b, room = render_compare_controls(neighbourhoods, room_options)
        cfilters = replace(filters, neighbourhoods=None, room_types=(room,))
        result, error = None, None
        if area_a == area_b:
            error = 'Choose two different neighborhoods to compare.'
        else:
            try:
                result = cached_compare(sha, normalized_key(cfilters), (area_a, area_b))
            except ValueError as exc:
                error = str(exc)
        render_compare(result, filters, area_a, area_b, room, error)
    with details:
        render_listings(data['listings'], filters, detail_area)
        render_methods(read_audit(sha), sha, filter_text, CONTRACT)
    st.caption(f'Render time this run: {time.perf_counter() - started:.2f} s')


main()
