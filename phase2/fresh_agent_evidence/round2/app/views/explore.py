"""Explore tab (U1, U3, U4): KPI cards, ranked bars, price CDF, neighborhood map, segment table.

Receives backend tables only; ranking calls the backend's rank_market_segments.
Selection changes go through the explicit `on_detail_select(neighbourhood)` callback.
"""
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from phase2.backend import rank_market_segments
from views.common import (MIN_N, TOP_N, MISSING_GRAY, usd, pct, num, count, room_label,
                          unique_short_names, finite_max)

FONT = dict(color='#1F2328')
BASE_LAYOUT = dict(paper_bgcolor='white', plot_bgcolor='white', font=FONT,
                   margin=dict(l=10, r=10, t=60, b=40))


# ---------------------------------------------------------------- KPI row
def render_kpis(overview, affordability, filters):
    o, a = overview.iloc[0], affordability.iloc[0]
    label = room_label(filters.room_types)
    if label == 'Mixed room types':
        st.caption('**Mixed room types**: KPI cards summarize all selected room types together; '
                   'rankings and comparisons below are always per room type.')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Matching listings', count(o.listing_count),
              help='Selected listings (unique IDs) after all filters, including the nightly budget.')
    c1.caption(f'{label}')
    c2.metric('Median listed nightly price', usd(o.median_price),
              help='Median of selected observed prices; excludes unknown taxes/fees.')
    c2.caption(f'price_n = {count(o.price_n)}; missing price = {count(o.missing_price_n)}')
    if filters.budget_usd is None:
        c3.metric('Within-budget share (pre-budget)', 'Set a budget')
        c3.caption('Enter a nightly budget in the sidebar.')
    else:
        c3.metric('Within-budget share (pre-budget)', pct(a.within_budget_share),
                  help='Pre-budget priced listings with price ≤ budget ÷ pre-budget priced listings.')
        c3.caption(f'{count(a.within_budget_n)} of {count(a.price_n)} priced listings '
                   f'(population before the budget filter)')
    c4.metric('Reviewed listings', pct(o.reviewed_share),
              help='Share of selected listings with more than 0 total reviews. Not a rating.')
    c4.caption(f'observed review counts = {count(o.review_n)}')


# ---------------------------------------------------------------- bar charts
def _bar_figure(ranked, value_col, title, x_title, x_range, color_kwargs, hover, text_fmt):
    ranked = ranked.head(TOP_N)
    labels = unique_short_names(ranked.neighbourhood)
    fig = go.Figure(go.Bar(
        x=ranked[value_col], y=labels, orientation='h',
        marker=color_kwargs(ranked), customdata=np.stack(hover(ranked), axis=-1),
        hovertemplate=hover.template + '<extra></extra>',
        text=[text_fmt(v) for v in ranked[value_col]], textposition='outside', cliponaxis=False))
    fig.update_layout(**BASE_LAYOUT, title=dict(text=title, font=dict(size=14)),
                      height=max(260, 28 * len(ranked) + 130), showlegend=False)
    fig.update_xaxes(title_text=x_title, range=x_range, gridcolor='#E5E5E5', zeroline=True)
    fig.update_yaxes(title_text='Neighborhood', categoryorder='array', categoryarray=labels,
                     autorange='reversed')
    return fig


class _Hover:
    def __init__(self, fn, template):
        self.fn, self.template = fn, template

    def __call__(self, frame):
        return self.fn(frame)


def render_price_bars(segments, room_types):
    st.subheader('Lowest median listed nightly price by neighborhood (USD/night)')
    ranked_all = rank_market_segments(segments, metric='median_price', min_n=MIN_N, ascending=True)
    if ranked_all.empty:
        st.info(f'No neighborhood/room segment has at least {MIN_N} observed prices under these filters. '
                'Small groups remain in the segment table and map.')
        return
    shown = pd.concat([ranked_all.loc[ranked_all.room_type.eq(r)].head(TOP_N) for r in room_types])
    xmax = finite_max(shown.median_price) * 1.15  # shared 0-to-max scale across room panels
    cmax = finite_max(shown.median_price)
    hover = _Hover(lambda f: [f.neighbourhood, f.price_p25, f.price_p75, f.listing_count, f.price_n,
                              f.missing_price_n],
                   '<b>%{customdata[0]}</b><br>Median: $%{x:,.0f}/night<br>'
                   'Q1–Q3: $%{customdata[1]:,.0f}–$%{customdata[2]:,.0f}<br>'
                   'Listings: %{customdata[3]:,}<br>price_n: %{customdata[4]:,}<br>'
                   'Missing price: %{customdata[5]:,}')
    color = lambda f: dict(color=f.median_price, colorscale='Viridis', cmin=0, cmax=cmax,
                           colorbar=dict(title='Median USD/night', tickprefix='$'))
    for room in room_types:
        ranked = ranked_all.loc[ranked_all.room_type.eq(room)]
        excluded = int(segments.loc[segments.room_type.eq(room)].price_n.lt(MIN_N).sum())
        if ranked.empty:
            st.caption(f'{room}: no segment with price_n ≥ {MIN_N}; see the segment table.')
            continue
        title = (f'{room}: top {min(TOP_N, len(ranked))} lowest median listed USD/night, '
                 f'selected listings (segments with price_n ≥ {MIN_N})')
        st.plotly_chart(_bar_figure(ranked, 'median_price', title, 'Median listed nightly price (USD)',
                                    [0, xmax], color, hover, lambda v: usd(v)),
                        key=f'price_bars_{room}', config={'displaylogo': False})
        st.caption(f'{excluded} {room} segment(s) with price_n < {MIN_N} are not ranked (display rule, '
                   f'not statistical significance); missing prices are excluded from medians.')


def render_affordability_bars(affordability_segments, filters, room_types):
    st.subheader('Highest within-budget share by neighborhood (pre-budget population, %)')
    if filters.budget_usd is None:
        st.info('Set a nightly budget in the sidebar to rank neighborhoods by within-budget share.')
        return
    ranked_all = rank_market_segments(affordability_segments, metric='within_budget_share',
                                      min_n=MIN_N, ascending=False)
    if ranked_all.empty:
        st.info(f'No segment has at least {MIN_N} pre-budget observed prices.')
        return
    hover = _Hover(lambda f: [f.neighbourhood, f.within_budget_n, f.price_n, f.listing_count],
                   '<b>%{customdata[0]}</b><br>Within budget: %{x:.1f}%<br>'
                   'Numerator (priced ≤ budget): %{customdata[1]:,}<br>'
                   'Eligible priced listings (pre-budget price_n): %{customdata[2]:,}<br>'
                   'Pre-budget listings: %{customdata[3]:,}')
    color = lambda f: dict(color=f.within_budget_share * 100, colorscale='Viridis', cmin=0, cmax=100,
                           colorbar=dict(title='Within budget (%)', ticksuffix='%'))
    for room in room_types:
        ranked = ranked_all.loc[ranked_all.room_type.eq(room)].copy()
        if ranked.empty:
            st.caption(f'{room}: no segment with pre-budget price_n ≥ {MIN_N}.')
            continue
        ranked['share_pct'] = ranked.within_budget_share * 100
        title = (f'{room}: top {min(TOP_N, len(ranked))} within-budget share (price ≤ '
                 f'{usd(filters.budget_usd)}), % of pre-budget priced listings')
        st.plotly_chart(_bar_figure(ranked, 'share_pct', title, 'Listings within budget (% of pre-budget priced)',
                                    [0, 105], color, hover, lambda v: f'{v:.1f}%'),
                        key=f'afford_bars_{room}', config={'displaylogo': False})
    st.caption('Denominator is every priced listing matching all filters except the budget; '
               'the budget-filtered Explore population is never used as the denominator.')


# ---------------------------------------------------------------- CDF
def render_price_cdf(distribution, filters, room_types):
    st.subheader('Price distribution, not a time trend (pre-budget listings)')
    if distribution.empty:
        st.info('No observed prices for the pre-budget population (price_n = 0); no distribution is drawn.')
        return
    log_x = st.toggle('Log-scale x-axis (USD/night, log10)', value=False, key='cdf_log_x')
    fig = go.Figure()
    for room in room_types:
        part = distribution.loc[distribution.room_type.eq(room)]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part.nightly_price_usd, y=part.cumulative_share * 100, mode='lines', line_shape='hv',
            name=f'{room} (price_n={int(part.price_n.iloc[0]):,})',
            customdata=part[['price_n']].to_numpy(),
            hovertemplate=(f'{room}<br>Price: $%{{x:,.0f}}/night<br>Cumulative: %{{y:.1f}}%'
                           '<br>price_n: %{customdata[0]:,}<extra></extra>')))
    if filters.budget_usd is not None:
        fig.add_vline(x=filters.budget_usd, line_dash='dash', line_color='#444',
                      annotation_text=f'Budget {usd(filters.budget_usd)}', annotation_position='top left')
    fig.update_layout(**BASE_LAYOUT, height=420,
                      title=dict(text='Cumulative % of priced listings at or below each listed USD/night '
                                      '(pre-budget, one step line per room type)', font=dict(size=14)),
                      legend=dict(orientation='h', yanchor='top', y=-0.2, x=0))
    fig.update_xaxes(title_text='Listed nightly price (USD, log scale)' if log_x else 'Listed nightly price (USD)',
                     type='log' if log_x else 'linear', tickprefix='$', gridcolor='#E5E5E5')
    fig.update_yaxes(title_text='Cumulative % of priced listings', range=[0, 100], ticksuffix='%',
                     gridcolor='#E5E5E5')
    st.plotly_chart(fig, key='price_cdf', config={'displaylogo': False})


# ---------------------------------------------------------------- map
def _size_ref(max_count, max_px=40):
    return 2.0 * max(max_count, 1) / (max_px ** 2)


def render_map(map_table, affordability_map, filters, room_types, detail_area, on_detail_select):
    st.subheader('Neighborhood map: approximate centers of listing coordinates')
    options = ['Median listed nightly price (selected listings)']
    if filters.budget_usd is not None:
        options.append('Within-budget share (pre-budget population)')
    metric = st.radio('Map color metric', options, horizontal=True, key='map_metric')
    use_budget = metric.startswith('Within')
    mode = st.radio('Map display', ['Geographic (outline may need network)', 'Coordinate grid (offline)'],
                    horizontal=True, key='map_mode',
                    help='If the geographic outline cannot load, the coordinate grid keeps the same markers.')
    table = (affordability_map if use_budget else map_table).copy()
    # Hover always discloses pre-budget budget evidence when a budget is set.
    if filters.budget_usd is not None:
        afford = affordability_map[['neighbourhood', 'room_type', 'within_budget_n', 'price_n']].rename(
            columns={'within_budget_n': 'budget_num', 'price_n': 'budget_den'})
        table = table.merge(afford, on=['neighbourhood', 'room_type'], how='left', validate='one_to_one')
    else:
        table['budget_num'] = np.nan
        table['budget_den'] = np.nan
    if table.empty:
        st.info('No neighborhood markers for these filters.')
        return
    table['map_n'] = table.map_n.fillna(0).astype(int)
    mappable = table.loc[table.latitude.notna() & table.longitude.notna()]
    omitted_listings = int(table.listing_count.sum() - table.map_n.sum())
    omitted_segments = int(len(table) - len(mappable))
    population = ('pre-budget population (all filters except budget)' if use_budget
                  else 'selected listings (all filters incl. budget)')
    value_col = 'within_budget_share' if use_budget else 'median_price'
    if use_budget:
        cmin, cmax, cbar = 0, 100, dict(title='Within budget (%)', ticksuffix='%')
    else:
        cmin, cmax, cbar = 0, finite_max(table.median_price), dict(title='Median USD/night', tickprefix='$')
    sizeref = _size_ref(int(table.listing_count.max()))
    geographic = mode.startswith('Geographic')
    st.caption(f'Color: {metric}. Marker area ∝ listing count (radius ∝ √count). Gray = no observed '
               f'price. Markers are mean valid listing coordinates, not boundaries or official centroids. '
               f'Omitted from map: {omitted_segments} segment(s), {omitted_listings:,} listing(s) without valid '
               f'coordinates (map_n excludes them).')
    legend_counts = sorted({int(v) for v in np.quantile(table.listing_count, [0.1, 0.5, 1.0])})
    for room in room_types:
        part = mappable.loc[mappable.room_type.eq(room)]
        if part.empty:
            st.caption(f'{room}: no mappable markers.')
            continue
        fig = go.Figure()
        values = part[value_col] * (100 if use_budget else 1)
        has = values.notna()
        custom = np.stack([part.neighbourhood, part.room_type, part.listing_count, part.map_n, part.price_n,
                           part.median_price.astype(float), part.missing_price_n,
                           part.budget_num.astype(float), part.budget_den.astype(float)], axis=-1)
        tmpl = ('<b>%{customdata[0]}</b> — %{customdata[1]}<br>Listings: %{customdata[2]:,} '
                '(map_n %{customdata[3]:,})<br>price_n: %{customdata[4]:,}; missing price: %{customdata[6]:,}'
                '<br>Median: $%{customdata[5]:,.0f}/night')
        if filters.budget_usd is not None:
            tmpl += '<br>Within budget (pre-budget): %{customdata[7]:,.0f} of %{customdata[8]:,.0f} priced'
        tmpl += f'<br><i>{population}</i><extra></extra>'
        selected_mask = part.neighbourhood.eq(detail_area).to_numpy() if detail_area else np.zeros(len(part), bool)
        for subset, colored in [(has, True), (~has, False)]:
            idx = subset.to_numpy()
            if not idx.any():
                continue
            marker = dict(size=part.listing_count[idx], sizemode='area', sizeref=sizeref, sizemin=3,
                          line=dict(width=np.where(selected_mask[idx], 3, 0.5),
                                    color=np.where(selected_mask[idx], '#D62728', '#333333').tolist()),
                          opacity=0.85)
            if colored:
                marker.update(color=values[idx], colorscale='Viridis', cmin=cmin, cmax=cmax, colorbar=cbar)
            else:
                marker.update(color=MISSING_GRAY)
            common = dict(customdata=custom[idx], hovertemplate=tmpl, mode='markers', marker=marker,
                          name='Observed' if colored else 'No observed value (gray)', showlegend=not colored)
            if geographic:
                fig.add_trace(go.Scattergeo(lat=part.latitude[idx], lon=part.longitude[idx], **common))
            else:
                fig.add_trace(go.Scatter(x=part.longitude[idx], y=part.latitude[idx], **common))
        for c in legend_counts:  # 3-symbol listing-count legend
            legend_marker = dict(size=[c], sizemode='area', sizeref=sizeref, color='rgba(0,0,0,0)',
                                 line=dict(color='#333', width=1))
            kw = dict(mode='markers', marker=legend_marker, name=f'{c:,} listings', hoverinfo='skip',
                      legendgroup='size', legendgrouptitle_text='Marker area = listing count')
            fig.add_trace(go.Scattergeo(lat=[None], lon=[None], **kw) if geographic
                          else go.Scatter(x=[None], y=[None], **kw))
        title = f'{room}: {metric}, neighborhood markers'
        fig.update_layout(**BASE_LAYOUT, height=520, title=dict(text=title, font=dict(size=14)),
                          legend=dict(orientation='h', yanchor='top', y=-0.02, x=0, itemsizing='trace'),
                          clickmode='event+select', dragmode='pan', uirevision=f'{room}-{metric}-{mode}')
        if geographic:
            fig.update_geos(fitbounds='locations', projection_type='mercator', showland=True,
                            landcolor='#F4F4F4', showcoastlines=True, coastlinecolor='#999',
                            showlakes=False, showcountries=False, showsubunits=True,
                            lataxis=dict(showgrid=True, gridcolor='#E0E0E0', dtick=0.25),
                            lonaxis=dict(showgrid=True, gridcolor='#E0E0E0', dtick=0.25))
        else:
            fig.update_xaxes(title_text='Longitude (°)', tickformat='.2f', gridcolor='#E5E5E5')
            fig.update_yaxes(title_text='Latitude (°)', tickformat='.2f', gridcolor='#E5E5E5',
                             scaleanchor='x', scaleratio=1.2)
        key = f'map_{room}'

        def _picked(key=key):
            state = st.session_state.get(key)
            points = (state or {}).get('selection', {}).get('points', []) if state else []
            for p in points:
                data = p.get('customdata')
                if data:
                    on_detail_select(data[0])
                    return
            on_detail_select(None)

        st.plotly_chart(fig, key=key, on_select=_picked, selection_mode='points',
                        config={'displaylogo': False, 'scrollZoom': True})


# ---------------------------------------------------------------- segment table
def segment_table(segments, affordability_segments, filters):
    t = segments.copy()
    if filters.budget_usd is not None:
        a = affordability_segments[['neighbourhood', 'room_type', 'within_budget_n', 'within_budget_share',
                                    'price_n']].rename(columns={
            'within_budget_n': 'pre_budget_within_budget_n', 'within_budget_share': 'pre_budget_within_budget_share',
            'price_n': 'pre_budget_price_n'})
        t = t.drop(columns=['within_budget_n', 'within_budget_share']).merge(
            a, on=['neighbourhood', 'room_type'], how='left', validate='one_to_one')
        t['pre_budget_within_budget_share'] = t.pre_budget_within_budget_share * 100
    else:
        t = t.drop(columns=['within_budget_n', 'within_budget_share'])
    t['reviewed_share'] = t.reviewed_share * 100
    t['small_sample_flag'] = np.where(t.price_n.lt(MIN_N), f'price_n<{MIN_N}', '')
    t = t.sort_values(['median_price', 'neighbourhood', 'room_type'], na_position='last').reset_index(drop=True)
    return t


def render_segment_table(segments, affordability_segments, filters, detail_area, on_detail_select):
    st.subheader('Segment evidence: every selected neighborhood × room type (selected listings)')
    t = segment_table(segments, affordability_segments, filters)
    if t.empty:
        st.info('No segments match these filters.')
        return
    query = st.text_input('Search neighborhoods in the table', key='segment_search',
                          placeholder='e.g. Venice')
    if query:
        t = t.loc[t.neighbourhood.str.contains(query, case=False, regex=False)].reset_index(drop=True)
    cfg = {
        'neighbourhood': st.column_config.TextColumn('Neighborhood'),
        'room_type': st.column_config.TextColumn('Room type'),
        'listing_count': st.column_config.NumberColumn('Listings', format='%d'),
        'price_n': st.column_config.NumberColumn('price_n', format='%d'),
        'missing_price_n': st.column_config.NumberColumn('Missing price', format='%d'),
        'median_price': st.column_config.NumberColumn('Median USD/night', format='$%.0f'),
        'price_p25': st.column_config.NumberColumn('Q1 USD/night', format='$%.0f'),
        'price_p75': st.column_config.NumberColumn('Q3 USD/night', format='$%.0f'),
        'pre_budget_within_budget_n': st.column_config.NumberColumn('Within budget n (pre-budget)', format='%d'),
        'pre_budget_within_budget_share': st.column_config.NumberColumn('Within budget % (pre-budget)', format='%.1f%%'),
        'pre_budget_price_n': st.column_config.NumberColumn('Priced n (pre-budget)', format='%d'),
        'reviewed_share': st.column_config.NumberColumn('Reviewed listings %', format='%.1f%%'),
        'review_n': st.column_config.NumberColumn('review_n', format='%d'),
        'median_total_reviews': st.column_config.NumberColumn('Median total reviews', format='%.1f'),
        'review_ltm_n': st.column_config.NumberColumn('review_ltm_n', format='%d'),
        'median_reviews_ltm': st.column_config.NumberColumn('Median reviews, source last 12 mo', format='%.1f'),
        'review_rate_n': st.column_config.NumberColumn('review_rate_n', format='%d'),
        'mean_observed_reviews_per_month': st.column_config.NumberColumn(
            'Mean reviews/month (observed rates only)', format='%.2f'),
        'availability_n': st.column_config.NumberColumn('availability_n', format='%d'),
        'median_available_nights': st.column_config.NumberColumn('Median available nights (0–365)', format='%.0f'),
        'small_sample_flag': st.column_config.TextColumn('Small-sample flag'),
    }
    order = [c for c in cfg if c in t.columns]
    selected_rows = t.index[t.neighbourhood.eq(detail_area)].tolist() if detail_area else []

    def _picked():
        rows = st.session_state.get('segment_table', {}).get('selection', {}).get('rows', [])
        on_detail_select(t.neighbourhood.iloc[rows[0]] if rows else None)

    st.dataframe(t, key='segment_table', column_order=order, column_config=cfg, hide_index=True,
                 height=min(420, 38 + 35 * len(t)), on_select=_picked, selection_mode='single-row',
                 selection_default={'selection': {'rows': selected_rows[:1], 'columns': []}})
    st.caption(f'Rows flagged price_n<{MIN_N} are shown but never ranked. Click a row to set the detail '
               'neighborhood (see “Listing details & methods”). Click a column header to sort.')


def render_explore(data, filters, room_types, detail_area, on_detail_select):
    render_kpis(data['overview'], data['affordability'], filters)
    if int(data['overview'].listing_count.iloc[0]) == 0:
        st.caption('No listings match these filters; counts show 0 and other metrics N/A.')
    render_price_bars(data['segments'], room_types)
    render_affordability_bars(data['affordability_segments'], filters, room_types)
    render_price_cdf(data['price_distribution'], filters, room_types)
    render_map(data['map'], data['affordability_map'], filters, room_types, detail_area, on_detail_select)
    render_segment_table(data['segments'], data['affordability_segments'], filters, detail_area,
                         on_detail_select)
