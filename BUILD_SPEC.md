# LA Airbnb Traveler Comparison Dashboard

Phase 2 build contract v1.1. Build the Phase 3 MVP from this file and `phase2/`.
Phase 1 remains unchanged. No host recruitment, revenue, occupancy, or investment scoring.

## 1. Revised traveler vision

A traveler planning a Los Angeles stay needs to shortlist neighborhoods and room
types that fit their nightly budget and stay length, then compare price and review
history before checking current listings on Airbnb. This dashboard replaces
inconsistent comparisons across individual search results with transparent,
like-for-like neighborhood summaries. It supports exploration, not live booking.

| Use case | User selects/inputs -> Dashboard shows -> User decides |
|---|---|
| U1: Find affordable areas | Room type, trip length, optional nightly budget -> matching listing count, median price, price spread, within-budget share and ranked neighborhoods -> choose areas to investigate. |
| U2: Compare alternatives | Exactly two neighborhoods and one room type -> same-filter price, affordability, review history and listing counts side by side -> choose which area better fits preferences. |
| U3: Understand geography | Metric and room type, then hover/click a neighborhood marker -> location, price, inventory, budget share and sample size -> add the neighborhood to a shortlist. |
| U4: Inspect evidence | Neighborhood/room row or map marker -> sortable listing table, missing-data warnings, review and minimum-stay details -> choose listings to check on Airbnb. |

These are the complete core use cases. Every feature below names its use case.

## 2. Starting view and controls

Use Streamlit, pandas and Plotly; one local process, no database or API keys. The
Phase 3 entry point is `app.py`. Start with **Explore**, all neighborhoods,
**Entire home/apt**, **7 planned nights**, no nightly budget, minimum total reviews
0, high-price sensitivity off. Show “Los Angeles listing snapshot; collection date
unknown; prices and availability may have changed.” Reset restores these defaults.

Global filter-bar controls (Phase 3 UI revision) apply immediately to every page:
neighborhood multiselect (empty = all neighborhoods), room-type dropdown (one type,
or “All room types” shown separately), stay-length number input of 1–365 nights,
nightly-budget dropdown of preset or custom positive USD amounts, minimum total
reviews dropdown, and “Hide flagged high prices” toggle. Offer a clearly labeled
empty stay-length box (**any stay length**); this sets trip nights to None and includes unknown
minimum stays. No date-range, season, bedrooms, bathrooms,
guest-capacity or rating filters: those facts are absent. Room type is not bedrooms.
Unknown minimum stay is excluded whenever a specific trip length is active.

Pages (sidebar navigation): **Explore**, **Compare neighborhoods**, **Listings & methods**.
Explore may show multiple room types as separate panels/series. Never pool room
types for a ranking or comparison. With multiple room types selected, show a
separate four-card KPI row for each room type: count, median price, budget share
and reviewed share. An optional combined count must say “Mixed room types”; do
not show pooled price/review/budget KPI cards. Compare has its own single-room
selector; changing the global Explore room selection does not change that selector.

## 3. Metrics and population rules

Canonical input: `phase2/outputs/listings.csv`; one row per listing `id`, one
snapshot. All metrics use the current filters unless the population below says
**pre-budget**: apply every filter except the nightly budget. The selected
population then additionally requires observed price <= budget when budget is on.
Price is treated as listed USD per night, excluding unknown taxes/fees/discounts;
it is not a dated quote or total trip cost. No imputation. Never average segment
medians to calculate a market median. Recompute from listing rows.

| Display / source columns | Calculation and denominator | Traveler question |
|---|---|---|
| Matching listings / `id` | Count selected rows (unique IDs); 0 if empty | How many snapshot listings meet these filters? |
| Median listed nightly price / `price` | Median selected nonmissing prices; show `price_n` and missing count | What is a typical listed nightly price? |
| Middle 50% price range / `price` | Linear-interpolated 25th–75th percentiles of selected observed prices | How spread out are listed prices? |
| Within-budget listings and share / `price` | **Pre-budget** count price <= budget divided by **pre-budget** observed-price count; null with no budget or no observed prices | How much of this area's priced inventory fits my budget? |
| Reviewed listings / `number_of_reviews` | Share selected rows with >0 total reviews; disclose observed count | How often is there any review history? |
| Median total reviews / `number_of_reviews` | Median selected observed values, including real zeros; show `review_n` | How much accumulated review history is typical? |
| Median reviews in source's last 12 months / `number_of_reviews_ltm` | Median observed values including zeros; show `review_ltm_n`; window is source-relative, not today-relative | How much review activity did the source record? |
| Mean observed reviews/month / `reviews_per_month` | Optional detail only: mean nonmissing source rates; show `review_rate_n` and “observed rates only” | What rate was reported among listings with a rate? |
| Calendar availability context / `availability_365` | Median observed nights, scale 0–365; show `availability_n` | How many nights did the source mark available in its forward window? |
| Stay compatibility / `minimum_nights` | Listing qualifies if minimum nights <= planned nights; not proof of booking eligibility | Does its listed minimum stay fit my plan? |

No review counts become ratings, quality scores or safety endorsements. Annual
availability is a secondary detail, not a booking confirmation or occupancy proxy.
No “best neighborhood” composite: allow users to weigh price and review evidence.

## 4. Views and interactions

| View / use case | Visual, ordering, encoding, interaction and backend |
|---|---|
| Explore KPI row / U1 | Four cards: matching listings, median nightly price with `price_n`, within-budget share with numerator/denominator (or “Set a budget”), reviewed-listing share. Use `dashboard_data()['overview']` for selected KPIs and `['affordability']` for budget share. |
| Neighborhood price / U1 | Horizontal bars, top 15 lowest medians per room type, ascending, USD x-axis starting at 0, neighborhood y-axis. Use selected `segments`, `rank_market_segments(metric='median_price')`. Tooltip: median, Q1/Q3, listing count, price_n, missing-price count. Intensity encodes price using a sequential Viridis palette and labeled USD color scale. |
| Affordability / U1 | When budget is set, horizontal bars top 15 highest within-budget shares per room type, 0–100% x-axis. Rank **pre-budget** `affordability_segments` by `within_budget_share`, descending. Show eligible-priced count and numerator on hover; the denominator must never be the budget-filtered subset. |
| Price distribution / U1 | Empirical cumulative **step line**, pre-budget data, x = listed USD/night, y = cumulative percent of priced listings, 0–100%. One series per selected room type; tooltip price, cumulative %, price_n. Optional vertical budget line. Label “Price distribution, not a time trend.” Default x limit is full observed range; an explicit log-x display toggle is allowed with positive values and clear log label. `price_distribution()` supplies every observed price point. |
| Geographic overview / U3 | Plotly geographic scatter using neighborhood/room summary markers, not listing pins. One panel per room type. Marker location = mean valid listing coordinates; approximate center, not official centroid/boundary. Color by median USD/night or within-budget %; marker **area** proportional to listing_count (radius proportional to square root of count). Include colorbar and 3-symbol count legend. All data fit initially; enable pan/zoom and scale bar where the map component supports it. `geographic_summary()` supplies metrics and map_n. |
| Map hover/click / U3, U4 | Hover shows neighborhood, room type, listing_count, map_n, selected price_n, median price, missing-price count and budget numerator/denominator. The bundle's `map` keeps selected price/inventory and supplies joined **pre-budget** within_budget_n/share plus `pre_budget_price_n`; never label selected price_n as the budget denominator. Use `affordability_map` for **pre-budget** budget-colored markers and label its different population. Click selects the neighborhood only, even from a room-specific panel; preserve all globally selected room types in Details. Highlight all segment rows for that neighborhood. Clearing selection restores global scope. A keyboard-accessible neighborhood dropdown offers identical behavior. |
| Compare neighborhoods / U2 | Independent two-neighborhood selectors default Hollywood and Venice; exactly one room type defaults Entire home/apt. Inherit global stay length, budget, reviews and sensitivity; ignore global neighborhood selection. `compare_neighbourhoods()` returns **pre-budget** side-by-side values. Show median price + IQR, budget count/share, total/last-12-month reviews, and sample sizes. Show A−B in USD for median price, percentage points for budget share; relative price difference (A/B−1) only when B>0. Label comparison A and reference B. No mixed-room or unmatched-filter comparison. |
| Segment evidence / U1, U4 | Full searchable/sortable table of selected neighborhood-room segments with metric denominators, missing counts and availability context. If budget is active, join within_budget_n/share and pre_budget_price_n from `affordability_segments` by neighborhood+room type, one-to-one; label these columns pre-budget. Initial sort median price ascending then neighborhood and room type. Show all segments, including small samples; flag metric n<30. Row click opens details. |
| Listing evidence / U4 | Selected listing rows: id (string), neighborhood, room type, listed price, minimum nights, total reviews, source last-12-month reviews, last_review, availability nights and flags. Sort price ascending, null last, id as tie-breaker. Paginate 50 per page. Airbnb link `https://www.airbnb.com/rooms/{id}`, labeled “Check current details”; do not describe a listing as available. Download all filtered detail-scoped rows, not just the current page, with only displayed columns and quoted string IDs; label button “Download all filtered listings (N rows)”. No host names/license strings needed in UI. |
| Methods / U4 | Source fingerprint and unknown snapshot date, actual row/missing counts, active filters, metric definitions, outlier threshold, caveats, and link to data contract. Make missingness visible next to charts, not only hidden here. |

Neighborhood markers satisfy hoverable geographic exploration with the current
source. No boundary file exists, so do not invent colored region polygons.
Choropleths are a later extension only after validated GeoJSON and a complete
neighborhood-key join. Geographic extents and region sizes must not imply density.

Implementation decisions settled by the fresh-agent test:
- Keep one authoritative detail-neighborhood state. Mouse and keyboard selection
  write the same state; clear/Reset must not be overwritten by stale chart/table
  selection on rerun. Selecting a row need not switch tabs automatically.
- The coordinate-grid fallback may be the default; an optional online map must
  fit the full current coordinate extent, rather than use a fixed zoom. Use three
  distinct representative count symbols when possible; for fewer than three
  distinct counts, show every distinct count. A labeled degree grid satisfies
  the offline scale; a supported geographic scale bar remains component-dependent.
- Listing sorting controls apply to the entire detail-scoped population **before**
  the 50-row page slice. Default price ascending/null-last/string-ID tie-break
  remains; offer price, total reviews and source last-12-month reviews with an
  ascending/descending control, resetting page to 1 on scope/sort changes.
- Render four cards in a desktop row and stack on narrow screens. Long labels
  must wrap/truncate with full hover text. Vertical-only prototype cards do not
  constitute final desktop layout acceptance.
- Methods may offer the data contract as both in-app rendered text and download;
  use a stable repository permalink once the submitted revision is available.

## 5. Visual and interaction acceptance rules

- Every chart/table has a specific title naming metric, population and unit; include axis labels, scale and legend where encoding requires them. Currency `$`, nights and percentages use explicit units. KPI prices show whole USD; percentages 1 decimal; no false precision in coordinates.
- White background, dark readable text, consistent spacing, sequential color scales for magnitude, gray for missing. Never encode missing as zero. Color is supported by labels/tooltips. Keep scales fixed within comparisons and unchanged while hovering; recompute only when filters/metric change. For price use the same shared 0-to-maximum scale across room panels; for affordability use 0–100%.
- Horizontal bars, wrapped/truncated neighborhood names with full hover text, top 15 visible, responsive height and table scrolling prevent overlap. At 1280×800 and 375px mobile width, no clipped legends or overlapping labels. Stack charts and cards on narrow screens.
- Ranked metrics require their own observed denominator >=30 (price_n for price and affordability). Label this as a display rule, not statistical significance. Small groups remain visible in the table/map with a warning; no numeric “winner” for either comparison group below the metric's threshold.
- If selected population is empty, show 0 listings, selected statistics “N/A”, and “No listings match these filters” with Reset. When pre-budget data still exists (e.g., budget below every price), keep its CDF, affordability bars/map and comparison visible, labeled pre-budget; budget share is 0%, not N/A, when price_n>0. If pre-budget population is also empty, replace those charts with an empty message. No blank chart crashes. Missing-price-only groups show counts and gray/N/A price encodings; hide unmappable markers and disclose omitted map_n separately. No CDF for groups with price_n=0.
- Explore budget filtering and pre-budget affordability must be distinguishable by labels. A budget must never force affordability to 100%. All tab filters and selection state remain visible. Hover changes no state; marker/table clicks change only detail scope, not global filters. Reset clears detail selection.
- Line charts show distributions in this MVP. Monthly, seasonal, MoM and YoY plots require repeated comparable snapshots or dated review/calendar observations with documented windows; do not infer them from each listing's last_review.

## 6. Architecture and technical choices

| Component | Input -> output / responsibility |
|---|---|
| `phase2/clean_data.py` | Raw all-string dataframe -> canonical dataframe + audit; load canonical CSV with explicit nullable types and string identifiers. No UI. |
| `phase2/build.py` | Immutable `LA_listings.csv` -> versioned canonical CSV, audit, manifest and representative dashboard tables. Rebuild offline; no external joins. |
| `phase2/backend.py` | Dataframe + immutable `Filters` -> values/dataframes. Filtering, KPI aggregation, ranking, distribution, geography and comparison have separate jobs. No mutable global data, prints, file reads or Streamlit dependencies. |
| `app.py` (Phase 3) | Render controls and coordinate state; call backend. No metric formulas duplicated in chart code. Compare deltas are presentation transforms of backend values. |
| `views/` (Phase 3) | Separate Explore, Compare and Details rendering functions receive tables and explicit selection callbacks. Chart changes do not alter cleaning. |
| `phase2/test_backend.py` | Independent source reconciliation, filter/denominator/edge cases and fresh-process reproducibility -> JSON verification. |

CSV fits ~44k rows and preserves a human-inspectable handoff; use explicit dtypes
on every load. Keep one canonical full dataset, not different cleaned copies per
view. The source remains immutable. The manifest pins source/output hashes.
Phase 2 requirements are in `phase2/requirements.txt`. Before building the UI,
run `python -m pip install -r phase2/requirements-dashboard.txt` for the exact
Streamlit/Plotly versions exercised by the fresh-agent build. Start Phase 3 with
`python -m streamlit run app.py` from the repository root. The existing root
requirements belong to earlier work. No services, secrets or database needed.

In Phase 3 cache canonical loading by canonical file SHA-256 using
`st.cache_data`; cache aggregation by hash plus normalized Filters tuple. Clear
cache when hash changes. Do not cache UI selection in backend. Render aggregated
map points (hundreds), paginate listing rows, and cap bars at 15; do not push 44k
listing markers into the browser. Profile on the developer laptop: aim for cold
load <5s and cached filter changes <1s; report unseen-filter computation separately
from repeated-filter cache hits and separate first-use environment/font setup
from warm startup. Record timings and optimize if they miss. These are Phase 3
acceptance targets, not claimed benchmark results.
Use a standard pip environment on deployment, repository-relative paths and
Streamlit-compatible hosting; data and environment rebuild must work without
machine-specific paths. A network basemap may fail offline: retain geographic
markers on a coordinate/grid fallback, and always keep the table usable.

## 7. Build order and checks

1. From repository root, install `phase2/requirements.txt`; run `python -m phase2.build`
   then `python -m phase2.test_backend`. Review `phase2/outputs/audit.json` and
   `verification.json`. No editing of Phase 1 or earlier submission artifacts.
2. Confirm team cleaning resolutions and merge this canonical package into main;
   see `phase2/RECONCILIATION.md`. Do not claim this happened before branch evidence.
3. Create `app.py` and views, wire global controls and default KPI/segment table.
4. Add price/affordability bars and step CDF; verify selected versus pre-budget
   counts with exported example scenarios, including budget250.
5. Add geographic markers, hover, detail selection and keyboard equivalent; test
   omitted coordinates, small groups and network fallback.
6. Add same-room comparison and listing detail pagination/export. Never create a
   rating, occupancy or availability-for-trip inference.
7. Check empty results, all missing prices, minimum stay at exactly trip length,
   0 reviews versus missing rates, outlier toggle, reset, shared scales, mobile
   layout, clean environment startup and response timings.

Concrete data checks: canonical rows 43,932 and unique string IDs; 5,570 prices,
11 minimum stays, 11,311 monthly review rates and 30,740 licenses missing; full-market
median observed price $224. All observed numeric values and identifier digits
match the source. A 7-night stay includes minimum_nights=7 and excludes 8/unknown.
For any $250 budget, affordability numerator equals selected priced listings and
denominator equals pre-budget price_n. Empty result count=0 and median=N/A.
Changing room type must change all relevant views; hovering never changes filters.

Fresh-agent build check before submission: use a clean checkout, give an independent
agent this spec and ask it to build Phase 3. Record every question/guess and fix the
contract. Automated fresh-process reruns are separate evidence and do not substitute
for that check. Findings, fixes and verification are recorded in
`phase2/FRESH_AGENT_TEST.md`; current completion status is in `phase2/READINESS.md`.
