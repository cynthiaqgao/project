"""Pure, reusable traveler metrics; no UI, files, caches, or hidden filter state."""
from dataclasses import dataclass, replace
import math
import pandas as pd

@dataclass(frozen=True)
class Filters:
    neighbourhoods: tuple[str, ...] | None = None
    room_types: tuple[str, ...] | None = ('Entire home/apt',)
    trip_nights: int | None = 7
    budget_usd: float | None = None
    min_reviews: int = 0
    exclude_high_prices: bool = False

    def __post_init__(self):
        if self.trip_nights is not None and (isinstance(self.trip_nights, bool) or
                not isinstance(self.trip_nights, int) or not 1 <= self.trip_nights <= 365):
            raise ValueError('trip_nights must be an integer from 1 to 365, or None.')
        if self.budget_usd is not None and (not math.isfinite(self.budget_usd) or self.budget_usd <= 0):
            raise ValueError('Budget must be a finite positive USD nightly amount.')
        if isinstance(self.min_reviews, bool) or not isinstance(self.min_reviews, int) or self.min_reviews < 0:
            raise ValueError('min_reviews must be a nonnegative integer.')

def filter_listings(d, filters=Filters(), *, apply_budget=True):
    """None means all categories; an empty tuple means no selected categories."""
    mask = pd.Series(True, index=d.index)
    if filters.neighbourhoods is not None:
        mask &= d.neighbourhood.isin(filters.neighbourhoods)
    if filters.room_types is not None:
        mask &= d.room_type.isin(filters.room_types)
    if filters.trip_nights is not None:
        mask &= d.minimum_nights.le(filters.trip_nights).fillna(False)
    if filters.min_reviews:
        mask &= d.number_of_reviews.ge(filters.min_reviews).fillna(False)
    if filters.exclude_high_prices:
        mask &= ~d.price_high_outlier
    if apply_budget and filters.budget_usd is not None:
        mask &= d.price.le(filters.budget_usd).fillna(False)
    return d.loc[mask].copy()

def overview_metrics(d, budget_usd=None):
    """One metrics row; null metrics for empty denominators, counts remain zero.

    Pass the pre-budget population for affordability, otherwise the share is 100%.
    """
    n, priced = len(d), int(d.price.count())
    within = int(d.price.le(budget_usd).fillna(False).sum()) if budget_usd is not None else None
    return pd.DataFrame([{
        'listing_count': n, 'price_n': priced, 'missing_price_n': n - priced,
        'median_price': d.price.median() if priced else float('nan'),
        'price_p25': d.price.quantile(.25) if priced else float('nan'),
        'price_p75': d.price.quantile(.75) if priced else float('nan'),
        'within_budget_n': within,
        'within_budget_share': within / priced if priced and within is not None else float('nan'),
        'review_n': int(d.number_of_reviews.count()),
        'median_total_reviews': d.number_of_reviews.median(),
        'review_ltm_n': int(d.number_of_reviews_ltm.count()),
        'median_reviews_ltm': d.number_of_reviews_ltm.median(),
        # Missing review counts are not reviewed, but stay in the selected-
        # listing denominator instead of silently shrinking it.
        'reviewed_share': float(d.number_of_reviews.gt(0).fillna(False).sum() / n) if n else float('nan'),
        'review_rate_n': int(d.reviews_per_month.count()),
        'mean_observed_reviews_per_month': d.reviews_per_month.mean(),
        'availability_n': int(d.availability_365.count()),
        'median_available_nights': d.availability_365.median(),
    }])

SUMMARY_COLUMNS = ['neighbourhood', 'room_type', 'listing_count', 'price_n',
    'median_price', 'price_p25', 'price_p75', 'within_budget_n', 'within_budget_share',
    'median_total_reviews', 'median_reviews_ltm', 'reviewed_share', 'review_n',
    'review_ltm_n', 'review_rate_n', 'mean_observed_reviews_per_month',
    'availability_n', 'median_available_nights', 'missing_price_n']

def market_summary(d, budget_usd=None):
    rows = []
    for (area, room), frame in d.groupby(['neighbourhood', 'room_type'], sort=True, dropna=False):
        row = overview_metrics(frame, budget_usd).to_dict('records')[0]
        rows.append({'neighbourhood': area, 'room_type': room, **row})
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)

def room_type_overview(d, budget_usd=None):
    """One KPI row per room type, so KPI cards never pool room types."""
    rows = [{'room_type': room, **overview_metrics(frame, budget_usd).to_dict('records')[0]}
            for room, frame in d.groupby('room_type', sort=True)]
    return pd.DataFrame(rows, columns=['room_type'] + SUMMARY_COLUMNS[2:])

def rank_market_segments(summary, metric='median_price', min_n=30, ascending=True):
    denominators = {'median_price': 'price_n', 'within_budget_share': 'price_n',
                    'listing_count': 'listing_count', 'median_total_reviews': 'review_n',
                    'median_reviews_ltm': 'review_ltm_n', 'median_available_nights': 'availability_n'}
    if metric not in denominators or not isinstance(min_n, int) or min_n < 1:
        raise ValueError('Choose a supported ranking metric and positive integer minimum n.')
    ranked = summary.loc[summary[denominators[metric]].ge(min_n) & summary[metric].notna()].copy()
    ranked = ranked.sort_values([metric, 'neighbourhood', 'room_type'],
                               ascending=[ascending, True, True]).reset_index(drop=True)
    ranked.insert(0, 'rank', range(1, len(ranked) + 1))
    return ranked

def price_distribution(d):
    """Exact empirical price CDF, by room type. Step line, never a time series."""
    rows = []
    for room, frame in d.groupby('room_type', sort=True):
        counts = frame.price.dropna().value_counts().sort_index()
        cumulative = counts.cumsum()
        for price, count in counts.items():
            rows.append({'room_type': room, 'nightly_price_usd': float(price),
                         'listing_count_at_price': int(count), 'price_n': int(counts.sum()),
                         'cumulative_share': float(cumulative.loc[price] / counts.sum())})
    return pd.DataFrame(rows, columns=['room_type', 'nightly_price_usd',
        'listing_count_at_price', 'price_n', 'cumulative_share'])

def geographic_summary(d, budget_usd=None):
    """Neighborhood/room markers, approximate mean coordinate; no invented boundaries."""
    summary = market_summary(d, budget_usd)
    valid = d.loc[~d.coordinate_review & d.latitude.notna() & d.longitude.notna()]
    coordinates = valid.groupby(['neighbourhood', 'room_type'], as_index=False).agg(
        latitude=('latitude', 'mean'), longitude=('longitude', 'mean'), map_n=('id', 'size'))
    return summary.merge(coordinates, on=['neighbourhood', 'room_type'], how='left', validate='one_to_one')

def compare_neighbourhoods(d, filters, areas):
    """Side-by-side comparable areas; same one room type and all other controls."""
    if len(areas) != 2 or len(set(areas)) != 2 or any(a not in set(d.neighbourhood) for a in areas):
        raise ValueError('Select exactly two distinct known neighborhoods.')
    if filters.room_types is None or len(filters.room_types) != 1:
        raise ValueError('Comparison requires exactly one room type.')
    base = filter_listings(d, replace(filters, neighbourhoods=None), apply_budget=False)
    rows = []
    for area in areas:
        row = overview_metrics(base.loc[base.neighbourhood.eq(area)], filters.budget_usd).to_dict('records')[0]
        rows.append({'neighbourhood': area, **row})
    return pd.DataFrame(rows)

def dashboard_data(d, filters=Filters()):
    """Consistent contract for all views; affordability always uses pre-budget data."""
    base = filter_listings(d, filters, apply_budget=False)
    selected = filter_listings(d, filters)
    selected_map = geographic_summary(selected)
    pre_budget_map = geographic_summary(base, filters.budget_usd)
    budget_columns = pre_budget_map[
        ['neighbourhood', 'room_type', 'within_budget_n', 'within_budget_share', 'price_n']
    ].rename(columns={'price_n': 'pre_budget_price_n'})
    selected_map = selected_map.drop(columns=['within_budget_n', 'within_budget_share']).merge(
        budget_columns, on=['neighbourhood', 'room_type'], how='left', validate='one_to_one'
    )
    pre_budget_map['pre_budget_price_n'] = pre_budget_map['price_n']
    return {'overview': overview_metrics(selected),
            'affordability': overview_metrics(base, filters.budget_usd),
            'room_overview': room_type_overview(selected),
            'room_affordability': room_type_overview(base, filters.budget_usd),
            'segments': market_summary(selected),
            'affordability_segments': market_summary(base, filters.budget_usd),
            'map': selected_map,
            'affordability_map': pre_budget_map,
            'price_distribution': price_distribution(base),
            'listings': selected.copy()}
