# Canonical LA listings data contract

Version 1.0. Source `LA_listings.csv`, 43,932 rows, 19 columns.
Source SHA-256: `16007ed61afb75ffe44a69e7296bd50a71d61b2cce7cf885eb9d71d1dbd6f289`.
Inside Airbnb attribution comes from the project source documentation. The exact
upstream snapshot/download date is not established for these bytes. Another
member's differently hashed download cannot establish this file's date. Preserve
attribution and the provider's CC BY 4.0 notice in the Phase 3 methods view.

Canonical output: `phase2/outputs/listings.csv`, loaded only with
`phase2.clean_data.load_listings()`. Grain = one listing per unique `id` in one
snapshot. There are no joins. Repeated hosts are legitimate, not duplicate
listings. No bedrooms, bathrooms, ratings, guest capacity, travel-date calendar,
fees, bookings, property condition or transit-distance data is present.

## Source fields

| Column | In-memory type | Meaning and null handling |
|---|---|---|
| `id` | string | Listing key; mandatory, digit strings, unique. Preserve exact digits. |
| `name` | string | Listing title; text display only, no inferred quality. |
| `host_id` | string | Host key; preserve null and digits, not required for traveler metrics. |
| `host_profile_id` | string | Undocumented secondary identifier; never substitute for host_id. |
| `host_name` | string | Host display name; not used in dashboard outputs. |
| `neighbourhood_group` | string | Broad source geographic group; category, not a boundary file. Missing becomes Unknown. |
| `neighbourhood` | string | Main comparison category; missing becomes Unknown. |
| `latitude`, `longitude` | nullable Float64 | Decimal degrees; globally valid; screening flag controls map use only. |
| `room_type` | string | Entire home/apt, Private room, Shared room, Hotel room; missing Unknown; unexpected labels flagged. Not bedroom count. |
| `price` | nullable Float64 | Listed USD/night under project's source interpretation; positive if observed. Missing excluded only from price calculations or active budget filters. No fee/currency/time conversion performed. |
| `minimum_nights` | nullable Int64 | Positive minimum stay; 11 unknown values remain null. Specific trip filter excludes unknowns. |
| `number_of_reviews` | nullable Int64 | Nonnegative accumulated review count; true zero retained. Does not measure rating. |
| `last_review` | string YYYY-MM-DD | Last observed review date; null for never-reviewed listings. Not scrape date or a history of monthly activity. |
| `reviews_per_month` | nullable Float64 | Nonnegative source rate with undocumented exposure detail; 11,311 null rates retained, including zero-review listings. Never fill with zero. |
| `calculated_host_listings_count` | nullable Int64 | Source host inventory count, >=1 if observed; not recomputed or used for traveler ranking. |
| `availability_365` | nullable Int64 | Source-reported available nights 0–365 in its forward calendar window. Unknown snapshot date prevents calendar alignment. Unavailable can mean booked or blocked. |
| `number_of_reviews_ltm` | nullable Int64 | Nonnegative review count in source's last-12-month window; includes actual zeros. Not relative to today's date. |
| `license` | string | Unverified source registration/exemption text; blank and N/A become null. Never infer legal status. Preserve leading zeroes. |

Text normalization removes Unicode formatting characters (category Cf), collapses
whitespace and trims outside spaces; it preserves accents, punctuation and case.
It creates no inferred neighborhood aliases. This reconciles invisible-formatting
differences without changing numeric evidence.

## Derived columns

All flags are nonnullable bool (also in `audit.json` dtypes); CSV True/False is explicitly mapped on reload.

| Column | Exact rule |
|---|---|
| `price_missing` | price is null |
| `minimum_nights_missing` | minimum_nights is null |
| `never_reviewed` | number_of_reviews equals 0 |
| `review_fields_inconsistent` | Zero reviews with date/rate present, or positive reviews with date/rate absent |
| `review_counts_inconsistent` | number_of_reviews_ltm > number_of_reviews |
| `price_high_outlier` | Observed price > Q3 + 3×(Q3−Q1), full-source positive observed prices; threshold $1,276 for this file |
| `price_under_10` | Observed price < $10; retain |
| `minimum_nights_over_365` | minimum_nights >365; retain |
| `coordinate_review` | Missing coordinates or outside latitude [33,35], longitude [-119,-117]; broad screen, not a county boundary |
| `license_missing` | license is null after marker normalization |
| `room_type_unrecognized` | room_type outside four documented categories; includes Unknown |
| `license_status` | string: Unknown, Exemption claimed; unverified, or Reported; unverified |

High-price sensitivity uses the one fixed full-source threshold; filters never
recompute it. Nothing is dropped for unusual prices, missing data, long stays,
missing licenses or review anomalies. Exact repeated normalized rows are removed
and counted (none in this source). Missing/conflicting IDs, schema changes,
numeric parse failures, impossible values and invalid date strings stop the build
for investigation. The cleaner never silently chooses a duplicate ID's first row.

No future-date rule is inferred from last_review; no collection date is known.
The build is independent of wall-clock time. Float columns (price, reviews_per_month,
latitude, longitude) are parsed with correctly rounded Python `float`, not pandas'
fast parser, so values equal the source and outputs are byte-identical across
platforms. Source bytes and all observed numeric
values remain unchanged. Detailed before/after missingness is exported separately;
raw_blank_n excludes literal N/A, so four extra clean license nulls are intentional.

## Analysis table contracts

`Filters`: neighborhoods/room_types are tuples, None means all, empty tuple means
no selection. Defaults: all neighborhoods, Entire home/apt, 7 nights, no budget,
0 minimum reviews, no sensitivity exclusion. Input validation rejects invalid
trip lengths, nonfinite/nonpositive budgets and negative/noninteger review counts.

`overview_metrics`: one row even if empty. Counts are zero, undefined statistics
null, never fabricated zeros. `market_summary`: one row per neighborhood/room-type
pair with listing_count, price_n, missing_price_n, median_price, price_p25,
price_p75, within_budget_n/share, review_n, review_ltm_n, median_total_reviews,
median_reviews_ltm, reviewed_share, review_rate_n, mean_observed_reviews_per_month,
availability_n and median_available_nights. Empty input returns the same columns
with zero rows. See BUILD_SPEC metric table for populations/units.
`reviewed_share` counts observed number_of_reviews>0 over all selected rows;
an unknown count does not enter the numerator, remains null in source data, and
is excluded from review_n. It must not silently shrink the share's denominator.

`rank_market_segments`: filters by metric-specific observed count >=30 by default,
then sorts metric and stable alphabetical tie-breakers. No inference of
statistical significance. Budget shares use pre-budget inputs only.
`price_distribution`: one row per room type/observed price with frequency,
price_n and cumulative_share in [0,1]. `geographic_summary`: segment metrics plus
mean latitude/longitude and map_n; unavailable locations remain null. map_n is
valid-coordinate count, listing_count is all filtered segment rows. A map marker
is an approximate neighborhood location, not an exact listing or polygon centroid.

`compare_neighbourhoods`: exactly two known areas, exactly one room type, same
trip/review/sensitivity settings; pre-budget price and affordability evidence.
`room_type_overview`: one `overview_metrics` row per room type (columns `room_type`
plus the summary metrics), so KPI cards never pool room types.
`dashboard_data` returns overview, affordability, room_overview (selected),
room_affordability (pre-budget), segments,
affordability_segments, map, affordability_map, price_distribution and listings.
In the bundle's `map`, listing_count/price_n/median_price describe selected rows,
while within_budget_n/share and the explicit `pre_budget_price_n` describe the
same group's pre-budget population. These are joined one-to-one by neighborhood
and room type. `affordability_map` contains only pre-budget metrics and also
provides `pre_budget_price_n` (equal to its price_n). The raw
`geographic_summary()` helper aggregates only its argument; use the bundle for
selected markers with affordability tooltips. UI must not derive affordability
from the budget-filtered overview or reuse selected price_n as its denominator.
