"""Compare neighborhoods tab (U2): same room type, same non-neighborhood filters, pre-budget evidence.

Deltas are presentation transforms of backend values (A−B, A/B−1); no metric formulas here.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from views.common import MIN_N, usd, pct, num, count, is_missing


def _delta_usd(a, b):
    return 'N/A' if is_missing(a) or is_missing(b) else f'{float(a) - float(b):+,.0f} USD'


def _delta_pp(a, b):
    return 'N/A' if is_missing(a) or is_missing(b) else f'{(float(a) - float(b)) * 100:+.1f} pp'


def _relative(a, b):
    if is_missing(a) or is_missing(b) or float(b) <= 0:
        return 'N/A'
    return f'{(float(a) / float(b) - 1) * 100:+.1f}%'


def render_compare_controls(neighbourhoods, room_options):
    """Independent selectors; ignore the global neighborhood selection."""
    c1, c2, c3 = st.columns(3)
    default_a = neighbourhoods.index('Hollywood') if 'Hollywood' in neighbourhoods else 0
    default_b = neighbourhoods.index('Venice') if 'Venice' in neighbourhoods else min(1, len(neighbourhoods) - 1)
    area_a = c1.selectbox('Comparison neighborhood A', neighbourhoods, index=default_a, key='compare_a')
    area_b = c2.selectbox('Reference neighborhood B', neighbourhoods, index=default_b, key='compare_b')
    room_default = room_options.index('Entire home/apt') if 'Entire home/apt' in room_options else 0
    room = c3.selectbox('Room type (exactly one)', room_options, index=room_default, key='compare_room')
    return area_a, area_b, room


def render_compare(result, filters, area_a, area_b, room, error=None):
    st.subheader(f'{area_a} (A) vs {area_b} (B): {room}, same filters, pre-budget population')
    st.caption('Inherits the sidebar stay length, budget, minimum reviews and high-price setting; ignores the '
               'sidebar neighborhood selection. Values use every filter except the nightly budget '
               '(pre-budget), so the budget only defines the within-budget share.')
    if error:
        st.warning(error)
        return
    a = result.loc[result.neighbourhood.eq(area_a)].iloc[0]
    b = result.loc[result.neighbourhood.eq(area_b)].iloc[0]
    price_ok = int(a.price_n) >= MIN_N and int(b.price_n) >= MIN_N
    budget_on = filters.budget_usd is not None

    rows = [
        ('Matching listings (pre-budget)', count(a.listing_count), count(b.listing_count), '—', '—'),
        ('Median listed nightly price', usd(a.median_price), usd(b.median_price),
         _delta_usd(a.median_price, b.median_price) if price_ok else 'Not compared (n<30)',
         _relative(a.median_price, b.median_price) if price_ok else 'Not compared (n<30)'),
        ('Middle 50% price range (Q1–Q3)', f'{usd(a.price_p25)}–{usd(a.price_p75)}',
         f'{usd(b.price_p25)}–{usd(b.price_p75)}', '—', '—'),
        ('price_n / missing price', f'{count(a.price_n)} / {count(a.missing_price_n)}',
         f'{count(b.price_n)} / {count(b.missing_price_n)}', '—', '—'),
        ('Within-budget listings (n of priced)',
         f'{count(a.within_budget_n)} of {count(a.price_n)}' if budget_on else 'Set a budget',
         f'{count(b.within_budget_n)} of {count(b.price_n)}' if budget_on else 'Set a budget', '—', '—'),
        ('Within-budget share', pct(a.within_budget_share) if budget_on else 'Set a budget',
         pct(b.within_budget_share) if budget_on else 'Set a budget',
         (_delta_pp(a.within_budget_share, b.within_budget_share) if price_ok else 'Not compared (n<30)')
         if budget_on else 'N/A', '—'),
        ('Median total reviews (review_n)', f'{num(a.median_total_reviews, 1)} ({count(a.review_n)})',
         f'{num(b.median_total_reviews, 1)} ({count(b.review_n)})', '—', '—'),
        ('Median reviews, source last 12 months (review_ltm_n)',
         f'{num(a.median_reviews_ltm, 1)} ({count(a.review_ltm_n)})',
         f'{num(b.median_reviews_ltm, 1)} ({count(b.review_ltm_n)})', '—', '—'),
        ('Reviewed listings (>0 reviews)', pct(a.reviewed_share), pct(b.reviewed_share), '—', '—'),
        ('Median available nights, 0–365 (availability_n)',
         f'{num(a.median_available_nights)} ({count(a.availability_n)})',
         f'{num(b.median_available_nights)} ({count(b.availability_n)})', '—', '—'),
    ]
    table = pd.DataFrame(rows, columns=['Metric', f'A: {area_a}', f'B: {area_b}', 'A − B',
                                        'Relative price (A/B − 1)'])
    st.dataframe(table, hide_index=True, key='compare_table')
    if not price_ok:
        st.warning(f'At least one neighborhood has fewer than {MIN_N} observed prices for {room}; '
                   'values are shown but no numeric price or budget difference is declared (display rule, '
                   'not statistical significance).')

    fig = go.Figure()
    for label, row in [(f'A: {area_a}', a), (f'B: {area_b}', b)]:
        if is_missing(row.median_price):
            continue
        fig.add_trace(go.Bar(
            x=[float(row.median_price)], y=[label], orientation='h', name=label,
            marker_color='#31688E' if label.startswith('A') else '#35B779',
            error_x=dict(type='data', symmetric=False,
                         array=[float(row.price_p75) - float(row.median_price)],
                         arrayminus=[float(row.median_price) - float(row.price_p25)]),
            hovertemplate=(f'{label}<br>Median ${float(row.median_price):,.0f}<br>Q1–Q3 '
                           f'{usd(row.price_p25)}–{usd(row.price_p75)}<br>price_n {int(row.price_n):,}'
                           '<extra></extra>')))
    if fig.data:
        fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', height=240, showlegend=False,
                          title=dict(text=f'Median listed USD/night with middle-50% range, {room}, pre-budget',
                                     font=dict(size=14)), margin=dict(l=10, r=10, t=50, b=40))
        fig.update_xaxes(title_text='Listed nightly price (USD)', rangemode='tozero', tickprefix='$',
                         gridcolor='#E5E5E5')
        if budget_on:
            fig.add_vline(x=filters.budget_usd, line_dash='dash', annotation_text=f'Budget {usd(filters.budget_usd)}')
        st.plotly_chart(fig, key='compare_chart', config={'displaylogo': False})
    else:
        st.info('Neither neighborhood has an observed price under these filters.')
