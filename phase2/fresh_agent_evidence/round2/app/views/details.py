"""Listing details & methods tab (U4): paginated listing evidence, CSV export and methods."""
import csv
import math
import pandas as pd
import streamlit as st
from views.common import MIN_N, SNAPSHOT_NOTE, usd, count

PAGE_SIZE = 50
FLAG_LABELS = {
    'price_missing': 'price missing', 'minimum_nights_missing': 'min stay unknown',
    'price_high_outlier': 'high-price flag', 'price_under_10': 'price < $10',
    'minimum_nights_over_365': 'min stay > 365', 'review_fields_inconsistent': 'review fields inconsistent',
    'review_counts_inconsistent': 'review counts inconsistent', 'coordinate_review': 'coordinates screened',
}
COLUMNS = ['id', 'neighbourhood', 'room_type', 'price', 'minimum_nights', 'number_of_reviews',
           'number_of_reviews_ltm', 'last_review', 'availability_365', 'flags', 'airbnb_url']


def listing_table(listings, detail_area):
    t = listings if not detail_area else listings.loc[listings.neighbourhood.eq(detail_area)]
    t = t.copy()
    flags = [t[c].astype(bool).map({True: label, False: ''}) for c, label in FLAG_LABELS.items() if c in t]
    t['flags'] = (pd.concat(flags, axis=1).apply(lambda r: '; '.join(x for x in r if x), axis=1)
                  if len(t) and flags else pd.Series('', index=t.index, dtype='string'))
    t['airbnb_url'] = 'https://www.airbnb.com/rooms/' + t.id.astype(str)
    t = t.sort_values(['price', 'id'], na_position='last', kind='mergesort').reset_index(drop=True)
    return t[COLUMNS]


def to_csv_bytes(table):
    out = table.copy()
    out['id'] = out.id.astype(str)
    return out.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).encode('utf-8')


def render_listings(listings, filters, detail_area):
    scope = f'neighborhood “{detail_area}”' if detail_area else 'all selected neighborhoods (global scope)'
    st.subheader(f'Listing evidence: selected listings in {scope}, listed USD/night ascending')
    t = listing_table(listings, detail_area)
    if t.empty:
        st.info('No listings match these filters')
        return
    pages = max(1, math.ceil(len(t) / PAGE_SIZE))
    page = st.number_input(f'Page (1–{pages}, {PAGE_SIZE} listings per page)', min_value=1, max_value=pages,
                           value=1, step=1, key='listing_page')
    page = min(int(page), pages)
    view = t.iloc[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    st.dataframe(view, hide_index=True, key='listing_table', column_config={
        'id': st.column_config.TextColumn('Listing ID'),
        'neighbourhood': 'Neighborhood', 'room_type': 'Room type',
        'price': st.column_config.NumberColumn('Listed USD/night', format='$%.0f'),
        'minimum_nights': st.column_config.NumberColumn('Minimum nights', format='%d'),
        'number_of_reviews': st.column_config.NumberColumn('Total reviews', format='%d'),
        'number_of_reviews_ltm': st.column_config.NumberColumn('Reviews, source last 12 mo', format='%d'),
        'last_review': 'Last review date',
        'availability_365': st.column_config.NumberColumn('Source available nights (0–365)', format='%d'),
        'flags': 'Data flags',
        'airbnb_url': st.column_config.LinkColumn('Airbnb', display_text='Check current details'),
    })
    st.caption(f'Showing {len(view)} of {len(t):,} listings (page {page} of {pages}). Missing prices sort last; '
               'ID breaks ties. A link is not evidence that a listing is available for your dates.')
    st.download_button('Download filtered listings (CSV, all pages)', to_csv_bytes(t),
                       file_name='filtered_listings.csv', mime='text/csv', key='download_listings')


def render_methods(audit, canonical_sha, filter_text, data_contract_path):
    st.subheader('Methods, sources and caveats')
    st.markdown(f'**{SNAPSHOT_NOTE}**')
    st.markdown(
        f'- Source file `{audit.get("source_path")}`, SHA-256 `{audit.get("source_sha256")}`; '
        f'snapshot date: **unknown** (`snapshot_date = {audit.get("snapshot_date")}`).\n'
        f'- Canonical dataset `phase2/outputs/listings.csv`, SHA-256 `{canonical_sha}`.\n'
        f'- Rows: {count(audit.get("input_rows"))} source, {count(audit.get("output_rows"))} canonical; '
        f'exact duplicates removed: {audit.get("exact_duplicates_removed")}.\n'
        f'- Data from Inside Airbnb (per project source documentation), licensed CC BY 4.0.\n'
        f'- High-price flag threshold: {usd(audit.get("high_price_threshold_usd"))} '
        f'(full-source Q3 + 3×IQR; fixed, never recomputed by filters).')
    missing = audit.get('missing', {})
    st.markdown('**Missing values in the canonical dataset**')
    st.dataframe(pd.DataFrame([{'Column': k, 'Missing rows': v} for k, v in missing.items()
                               if k in ('price', 'minimum_nights', 'reviews_per_month', 'last_review',
                                        'license', 'host_id', 'latitude', 'longitude')]),
                 hide_index=True, key='methods_missing')
    st.markdown('**Active filters**')
    st.dataframe(pd.DataFrame(list(filter_text.items()), columns=['Control', 'Value']), hide_index=True,
                 key='methods_filters')
    st.markdown('**Metric definitions**')
    st.markdown(
        '- *Matching listings*: count of selected listings (unique IDs).\n'
        '- *Median listed nightly price*: median of selected observed prices (price_n); missing never imputed.\n'
        '- *Middle 50% range*: linear-interpolated 25th–75th percentile of selected observed prices.\n'
        '- *Within-budget share*: pre-budget listings priced ≤ budget ÷ pre-budget observed-price count '
        '(all filters except the budget).\n'
        '- *Reviewed listings*: share of selected listings with >0 total reviews. Review counts are not ratings.\n'
        '- *Median reviews in source last 12 months*: window relative to the unknown snapshot, not today.\n'
        '- *Mean reviews/month*: observed rates only (review_rate_n); missing rates are never zero-filled.\n'
        '- *Available nights*: source forward-calendar context 0–365, not occupancy or a booking confirmation.\n'
        '- *Stay compatibility*: minimum nights ≤ planned nights; not proof of booking eligibility.\n'
        f'- *Ranking display rule*: a ranked metric needs its own observed n ≥ {MIN_N}; not statistical significance.')
    st.markdown('**Caveats**: prices exclude unknown taxes, fees and discounts and are not dated quotes or '
                'total trip cost. No seasonal or monthly trends are inferred. Map markers are approximate '
                'neighborhood centers, not boundaries.')
    st.markdown(f'Full data contract: `{data_contract_path}` (in the repository).')
    try:
        with open(data_contract_path, encoding='utf-8') as fh:
            text = fh.read()
        with st.expander('Show data contract'):
            st.markdown(text)
    except OSError:
        st.caption('Data contract file not found next to the app.')
