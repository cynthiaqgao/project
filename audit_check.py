"""Reproducible check for my-audit.md (CR-XG-01).

Run from the extracted project root (the folder containing phase2/):
    python audit_check.py
Needs Python >= 3.10 (backend.py uses `X | None` annotations) and pandas.
"""
import sys

import pandas as pd

sys.path.insert(0, 'phase2')
from backend import Filters, dashboard_data  # noqa: E402

d = pd.read_csv('phase2/outputs/listings.csv', dtype={'id': str})

# Check 1: budget share on the real data, counted directly from listing rows
r = dashboard_data(d, Filters(budget_usd=250))
base = d.loc[(d.room_type == 'Entire home/apt') & (d.minimum_nights <= 7)]
priced = base.price.dropna()
print('direct count  :', (priced <= 250).sum(), len(priced), (priced <= 250).mean())
print(r['affordability'][['within_budget_n', 'price_n', 'within_budget_share']].to_string())

# Check 1b: hand-calculable small case ($100 and $300, budget $200 -> 1/2 = 50%)
two = d.head(2).copy()
two['room_type'] = 'Entire home/apt'
two['minimum_nights'] = 1
two['neighbourhood'] = 'X'
two['price'] = [100.0, 300.0]
s = dashboard_data(two, Filters(budget_usd=200))
print('small case affordability:', s['affordability'][['within_budget_n', 'price_n', 'within_budget_share']].to_dict('records'))
print('small case map          :', s['map'][['price_n', 'within_budget_n', 'within_budget_share']].to_dict('records'))
print('small case affordability_map:', s['affordability_map'][['price_n', 'within_budget_n', 'within_budget_share']].to_dict('records'))

# Check 2: does the selected-price map carry the pre-budget budget fields?
print('map rows with non-null budget share (of %d):' % len(r['map']),
      int(r['map'].within_budget_share.notna().sum()))
print('pre_budget_price_n in map columns:', 'pre_budget_price_n' in r['map'].columns)
