# Airbnb cleaning rules and decision log

## Analysis vision

A prospective Los Angeles Airbnb host must decide which broad location and room-type combination to investigate. The main comparison is median listed nightly price, supported by listing count, median availability, and recent-review activity. These are listing signals, not realized revenue, occupancy, or profit.

## Input and output grain

- Input: one Los Angeles Airbnb listing snapshot row per `id`.
- Expected unique key: `id`.
- Cleaned output: one listing per `id`.
- Comparison table: one `neighbourhood_group` and `room_type` combination per row.

## Proposed rules written before cleaning

| Field or issue | Proposed rule | Reason |
|---|---|---|
| Source preservation | Read `listings.csv`; never overwrite it. Write derived files under `outputs/`. | The assignment requires a reproducible path from the original source. |
| Identifiers | Load `id`, `host_id`, and `host_profile_id` as strings. Preserve leading zeros if they ever occur. | Identifiers are labels, not quantities. |
| Duplicate rows | Remove exact duplicate rows and report the count. | Exact repeats add no information. |
| Duplicate listing IDs | Require nonmissing, unique `id`; stop with an error instead of choosing a record arbitrarily. | A duplicate ID would violate the stated grain and needs investigation. |
| Numeric fields | Convert price, coordinates, minimum nights, review measures, host listing count, and availability with coercion; count all nonblank conversion failures. | Failed conversions must be visible rather than silently treated as valid numbers. |
| Dates | Parse `last_review` as a date and count failed nonblank values. | Valid dates are needed to interpret review recency. |
| Text | Strip outer whitespace, collapse repeated whitespace, and remove invisible Unicode format characters from text fields. Preserve capitalization and punctuation. | This standardizes labels while retaining meaningful listing wording. |
| Missing price | Keep the row, leave price missing, and add `price_missing_flag`. Exclude missing prices from price denominators. | A missing price cannot be imputed responsibly from this file. |
| Missing minimum nights | Keep the row, leave the value missing, and add `minimum_nights_missing_flag`. | The listing remains useful for non-minimum-night analysis. |
| Missing reviews per month | Fill with `0` only when `number_of_reviews == 0`, and flag the imputation. Otherwise retain missing. | In this snapshot, all 11,311 missing rates occur on zero-review listings, so zero represents the observed review count rather than an estimated rate. |
| Missing last review | Retain missing when a listing has no reviews. | A zero-review listing has no valid last-review date. |
| Missing host fields | Retain missing values and add `host_identity_missing_flag`. | Host details are not required for the planned location/room comparison. |
| Missing license | Retain missing and add `license_reported`. Do not interpret missing as illegal or reported as compliant. | The file alone cannot determine regulatory status. |
| Extreme prices | Retain values and add `price_outlier_flag` for prices above the full-data 99th percentile. Use medians in the main comparison. | High prices may be real luxury listings; flagging avoids an unsupported deletion. |
| Minimum nights above 365 | Retain and flag values above 365. | Unusual long-stay requirements may be genuine; they are not automatically data errors. |
| Review date after snapshot label | Retain and flag dates after the official `2026-06-15` snapshot path. | Ninety-seven dates fall from June 16–22; changing them would invent information. The discrepancy must limit recency claims. |
| More than 365 reviews in the last year | Retain and flag. | Multiple reviews per day may be possible for a multi-unit listing, but the values need investigation before interpreting them as ordinary listing activity. |
| Other validity checks | Require price to be positive when present, minimum nights to be positive when present, availability to be 0–365, reviews to be nonnegative, and coordinates to be globally valid. | Violations would be impossible or incompatible with the field definitions. |
| Merge handling | Do not merge tables in this assignment. | Only one source file is supplied. |
| Safe sample | Select up to 50 deterministic rows, deliberately including difficult cases. Exclude host names/IDs, exact coordinates, listing names, and license strings from the shareable sample. | The sample remains useful for inspection while reducing unnecessary personal/location detail. |

## Decision log after profiling

| Decision | Result |
|---|---|
| Treat missing `reviews_per_month` on zero-review rows as structural | Accepted: all 11,311 missing values have zero total reviews; no positive-review row has a missing rate. |
| Drop listings with missing price | Rejected: 5,570 rows would be lost and remain useful for availability/review analyses. Retained with a flag. |
| Delete extreme prices or long minimum stays | Rejected: the data provides no evidence they are entry errors. Retained with flags. |
| Deduplicate by `id` | Not needed for this snapshot: 0 repeated IDs and 0 exact duplicate rows. The script still validates this rule on every run. |
| Infer missing license or host information | Rejected: the necessary evidence is not in this file. |
| Treat the official snapshot label as a strict event cutoff | Revised after profiling: 97 `last_review` values occur after June 15. They are retained and flagged, and the discrepancy is documented as a source limitation. |
