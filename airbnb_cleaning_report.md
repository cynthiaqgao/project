# Module 6 Project Data Cleaning Report

**Project:** Los Angeles Airbnb Listing Market Comparison  
**Student:** Warner0405  
**Individual branch:** `Warner`

## Checklist for inspecting and cleaning data

### 1. State the vision along with a specific analysis question

**Status: Done**

A prospective Los Angeles Airbnb host must decide which broad location and room-type combination to investigate. The specific question is: **How do median listed nightly price, listing count, median availability, and recent-review activity compare across `neighbourhood_group` and `room_type` combinations?** The primary metric is median listed price, supported by its nonmissing denominator and the other listing signals. See `airbnb_cleaning_rules.md` and `outputs/market_comparison.csv`.

### 2. Define one row

**Status: Done**

One original and cleaned row represents one Airbnb listing in the Los Angeles snapshot. `id` is the expected unique key. The full-data checks found 43,932 rows, 43,932 unique nonmissing IDs, and no repeated IDs. The comparison output has one `neighbourhood_group`/`room_type` combination per row.

### 3. Preserve the source

**Status: Done**

The source is the Inside Airbnb Los Angeles summary `listings.csv` snapshot in the official `2026-06-15` path. The local copy is named `listings.csv`, has a local modification date of 2026-09-28, and has SHA-256 `d3b34461d0dc409dbe9f99573e3343e342dbcefbb0767b4b62d60b3beb4aceb2`. `clean_airbnb.py` reads but never overwrites it; all derived files go to `outputs/`. Access and rerun instructions appear in `README.md`.

### 4. Inspect columns and types

**Status: Done**

Identifiers are loaded as strings; whole-number measures use nullable integers; price, coordinates, and monthly review rate use numeric types; and `last_review` is parsed as a date. Nonblank conversion failures were 0 for every converted column: price, latitude, longitude, minimum nights, total reviews, reviews per month, calculated host listing count, availability, last-year reviews, and last-review date. Missing values remain distinct from conversion failures. Evidence: `outputs/cleaning_summary.json` under `conversion_failures`.

### 5. Standardize text

**Status: Done**

The script strips outer whitespace, collapses repeated whitespace, and removes invisible Unicode format characters while preserving capitalization and punctuation. Changed-value counts were: `name` 1,030, `host_name` 257, `license` 2, and 0 each for neighborhood group, neighborhood, and room type. For listing 2708, the host string containing invisible U+2068/U+2069 markers became `Chas.`. Identifiers remain strings so leading zeros would be preserved. Evidence: `outputs/five_record_checks.csv` and `outputs/cleaning_summary.json`.

### 6. Investigate duplicates

**Status: Done**

The original file contained 0 exact duplicate rows and 0 repeated nonblank listing IDs. No rows were removed. The script removes exact duplicates if present but stops for repeated IDs rather than deciding arbitrarily which listing record to keep.

### 7. Handle missing data

**Status: Done**

Important before/after counts are:

| Field | Before | After | Decision |
|---|---:|---:|---|
| `price` | 5,570 | 5,570 | Retain missing; add `price_missing_flag`; omit from price denominators. |
| `minimum_nights` | 11 | 11 | Retain missing; add a flag. |
| `last_review` | 11,311 | 11,311 | Retain because all correspond to zero-review listings. |
| `reviews_per_month` | 11,311 | 0 | Fill only zero-review rows with 0 and flag the imputation. |
| `host_id` | 181 | 181 | Retain; host fields are not required for the main comparison. |
| `host_name` | 384 | 384 | Retain and flag incomplete host identity. |
| `host_profile_id` | 395 | 395 | Retain and flag incomplete host identity. |
| `calculated_host_listings_count` | 181 | 181 | Retain; do not infer. |
| `license` | 30,736 | 30,736 | Retain; add `license_reported` without inferring legality. |

All 11,311 missing monthly review rates occur on zero-review rows, and no positive-review row has a missing monthly rate.

## Checklist for validating the result

### 8. Check suspicious values

**Status: Done**

There were 0 nonpositive prices, 0 nonpositive minimum stays, 0 negative review measures, 0 last-year review counts above total reviews, 0 availability values outside 0–365, and 0 globally invalid coordinates. The script retained and flagged 384 prices above the full-data 99th percentile ($2,905.17), 24 minimum stays above 365 nights, and 2 listings with more than 365 reviews in the last year because unusual does not prove incorrect. It also retained and flagged 97 last-review dates after the official June 15 snapshot path; those dates run through June 22 and are documented as a source-timing limitation.

### 9. Verify merges

**Status: Not applicable**

No tables were merged. This submission cleans one supplied listings file, so there are no merge keys, unmatched keys, or merge multiplication to report.

### 10. Reconcile changes

**Status: Done**

Starting rows: 43,932. Exact duplicates removed: 0. Final rows: 43,932. Difference: 0. The grouped comparison's `listing_rows` also sums to 43,932. Cleaning changes no price, availability, or review total; the only numeric fill is monthly review rate = 0 for 11,311 listings already known to have zero reviews.

### 11. Check calculations

**Status: Done**

Median price uses 38,362 listings with nonmissing price; missing prices are excluded by pandas and `listings_with_price` reports the denominator for every group. Availability and last-year review metrics each use all 43,932 listings. The group keys `neighbourhood_group` and `room_type` have no missing values, and grouped listing counts reconcile to the cleaned population. Median rather than mean price limits the influence of retained luxury-listing outliers. Availability is not occupancy, and recent reviews are not bookings or revenue.

### 12. Verify individual records

**Status: Done**

All five checks passed. Complete expected and actual strings are in `outputs/five_record_checks.csv`.

| Listing | Difficult case | Expected and actual result |
|---|---|---|
| 2708 | Invisible Unicode around host name | Remove only invisible format markers; cleaned value is `Chas.`. Match: True. |
| 9140 | Missing price | Keep price missing and set `price_missing_flag=True`. Match: True. |
| 584724 | Zero reviews and missing monthly rate | Fill monthly rate with 0 and set imputation flag. Match: True. |
| 1079335 | Minimum stay of 366 | Retain 366 and set over-365 flag. Match: True. |
| 7128675 | Review date after snapshot label | Retain 2026-06-16 and set after-snapshot flag. Match: True. |

### 13. Test reproducibility

**Status: Done**

From a fresh Python process in the repository folder, run:

```bash
~/dso576/00-setup/.venv/bin/python clean_airbnb.py
~/dso576/00-setup/.venv/bin/python verify_airbnb_outputs.py
```

The run recreated all five output files without spreadsheet edits. The verifier passed source hash, row reconciliation, unique key, numeric logic, flag counts, grouped reconciliation, safe-sample, and five-record assertions. A second fresh-process run produced byte-identical SHA-256 hashes for all five outputs. Notebook users should restart the kernel and run all cells as described in `README.md`.

### 14. Document remaining limitations

**Status: Done**

- Listed price is not realized average daily rate, and `availability_365` is not occupancy. The file cannot establish bookings, revenue, profit, or demand.
- Missing price affects 5,570 listings; price comparisons use 38,362 rows and may be biased if missingness differs systematically by group.
- The 97 last-review dates after the official snapshot path date create a timing discrepancy. Recency claims should remain cautious until Inside Airbnb's extraction semantics are confirmed.
- License missingness cannot establish whether a listing is legal, exempt, pending, or simply unreported.
- Extreme prices, long minimum stays, and very high review activity were retained because the file offers no basis for correction; flagged records should be investigated before record-level decisions.
- This is one cross-sectional snapshot. It cannot measure causal effects or market changes without additional snapshots or calendar/review data.
- Inside Airbnb is a third-party snapshot of public listings, not an Airbnb transaction system.

## Cleaning decision log

The full proposed-rule and revision log is in `airbnb_cleaning_rules.md`. The main revision after profiling was to add flags for dates after the snapshot label and for more than 365 reviews in the last year rather than modifying or deleting those records.

## Safe sample

`outputs/listings_cleaned_sample.csv` contains 50 deterministic rows. It includes difficult flagged cases and context rows selected with random seed 576. The sample omits host names and identifiers, exact coordinates, listing names, and license strings. Full-data checks—not the sample—support every reported count.

## Codex verification response

**Verification request:** Review the Module 6 Airbnb cleaning workflow for rule consistency, full-data evidence, row reconciliation, calculation denominators, five record checks, reproducibility, and unsupported claims.

**Codex response:** PASS with documented limitations. The source is preserved by hash; the workflow starts from `listings.csv`; 43,932 starting rows reconcile to 43,932 unique cleaned listing IDs; all numeric/date conversion failure counts are reported; missing-value actions match the stated rules; group counts reconcile; all five record checks pass; and a fresh-process verifier passes. The analysis appropriately uses median price with a 38,362-row denominator and does not relabel availability or reviews as occupancy, bookings, revenue, or profit. Remaining cautions are the 97 post-snapshot-label review dates, price and license missingness, retained extremes, and the cross-sectional third-party nature of the dataset.
