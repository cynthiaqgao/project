# Fresh agent test, round 2: questions, guesses and changes

Date: October 16, 2026. Project: LA Airbnb traveler dashboard (DSO 576 Phase 2).
Round 1 (Codex, same day) is in `FRESH_AGENT_TEST.md`. This is a second,
independent run by a different agent.

## Method

An independent Claude coding agent with no project history got a clean git
checkout containing `BUILD_SPEC.md` (v1.0), `LA_listings.csv` and `phase2/`, and
one instruction: "Read BUILD_SPEC.md and follow it to build the Phase 3 dashboard
MVP." No one answered its questions. It logged every question it would have asked
and every guess it made, then kept going.

It built `app.py` plus `views/` (Explore, Compare, Details), ran the documented
build and tests, and ran 17 headless Streamlit AppTest scenarios with zero
exceptions. Its raw log is `fresh_agent_evidence/round2/ROUND2_RAW_AGENT_LOG.md` and its app is in
`fresh_agent_evidence/round2/app/` (test artifact, not the Phase 3 dashboard).

Key numbers it reproduced: default view 16,633 listings, median $371; $250 budget
3,773 of 15,412 priced listings (24.5%), matching `budget250_*.csv`; empty
selection 0 listings and N/A; all stay lengths 32,454 listings.

## Questions it would have asked

| ID | Question | Impact | Resolution |
|---|---|---|---|
| Q1 | U3 says "add the neighborhood to a shortlist" but no shortlist control or state is specified anywhere. | High | Spec: Shortlist paragraph in §2 (button beside the detail dropdown, max 5, session only, sidebar list with remove, listed first in Compare, cleared by Reset). |
| Q2 | §7 step 2 asks to merge into main; an agent cannot get team approval. | Med | Spec: step 2 marked "Team gate, not an agent task". |
| Q3 | "Test network fallback" has no mechanism or pass rule; Plotly geo loads its outline from a CDN. | Med | Spec: "Map background" radio (Basemap / Coordinate grid); pass = grid mode shows every mappable marker with network off. |
| Q4 | How to verify 1280×800 and 375px layouts without a browser. | Med | Spec: browser dev tools responsive mode at 1280×800 and 375×812, screenshots saved as Phase 3 evidence. |

## Guesses it made

Impact: High changes a product, data, metric or interaction decision.

| ID | What was unclear | Agent's guess | Impact | Resolution |
|---|---|---|---|---|
| G1 | Streamlit/Plotly versions not pinned. | Used installed versions. | Med | Already fixed in round 1 (`requirements-dashboard.txt`). |
| G2 | Rebuild on a different machine rewrote committed `listings.csv` (252 coordinate rows) and manifest hashes. | Kept regenerated files. | High | **Real bug.** pandas' fast float parser is not correctly rounded (`34.094219852620036` became `34.09421985262004`). Fixed in `clean_data.py` with `exact_float()`; Mac and Linux builds now produce the identical hash `a6962eaf…`. |
| G3 | `default_*`/`budget250_*` CSVs not committed, so tests fail on a clean clone. | Ran build first. | Med | Partly a test setup artifact; on your Mac `phase2/` is still uncommitted. Resolves when phase2 is committed with outputs (gitignore already allows them). |
| G4 | `LA_listings.csv` not tracked. | Used working copy. | Med | False positive from the test copy; it is tracked in your repo. No change. |
| G5 | README mentions a notebook and `requirements-notebook.txt` that don't exist. | Ignored. | Low | False positive; both exist in your repo. No change. |
| G6 | "Numeric values match the source" held only under pandas' parser; tests skipped lat/long. | Passed with caveat. | Med | Test now compares price, rates, latitude and longitude as correctly rounded floats. Spec check reworded. |
| G7 | Contract says flags are plain bool; `audit.json` listed nullable `boolean`. | No change. | Low | Flags cast to bool before audit. |
| G8 | 265 pre-filled neighborhood chips. | Pre-filled all. | Low | Spec: "All neighborhoods" checkbox; off reveals an empty multiselect. |
| G9 | Budget widget form. | number_input, blank = none. | Low | Spec: blank = no budget, min $1, step $25. |
| G10 | "All stay lengths" form. | Checkbox. | Low | Spec: checkbox that disables the nights input. |
| G11 | Which tabs global controls affect. | Explore + Details. | Low | Spec: Explore and Details; Compare inherits only what its row lists. |
| G12 | Does global room type change Compare? | No. | Med | Already fixed in round 1. |
| G13 | Can KPI median price and reviewed share pool room types? | Pooled with a label. | High | Spec fixed in round 1 (one KPI row per room type). Round 2 added backend `room_type_overview()` and `room_overview`/`room_affordability` in `dashboard_data` so the UI doesn't recompute metrics. |
| G14 | With a budget the median price card is always ≤ budget; travelers could misread it. | Followed spec. | Med | Spec: label "Median of within-budget listings" plus "All priced: $X (pre-budget)". |
| G15 | With $250 only 30 of 229 segments qualify for price ranking. | Followed spec. | Med | Spec: price bars rank **pre-budget** segments; budget shown as a reference line. **Team should confirm.** |
| G16 | "Shared 0-to-maximum scale" maximum undefined. | Largest displayed bar. | Low | Spec: largest value displayed across room panels. |
| G17 | Panel layout for per-room bars. | Stacked charts. | Low | Spec: one stacked chart per room type. |
| G18 | CDF x range up to $20,583 squashes the curve. | Kept + log toggle. | Low | No change; log toggle already allowed. |
| G19 | Map scale bar requested; Plotly geo has none. | None. | Low | Spec: scale bar not required. |
| G20 | 3-symbol legend values. | p10/median/max. | Low | Spec: fixed 10, 100, 1,000. |
| G21 | Map color control unnamed, no default. | Radio. | Low | Spec: "Map color" radio, median price default. |
| G22 | With a budget, price-mode markers vanish for segments without within-budget listings. | Accepted. | Med | Spec: state their count beneath the map. Tooltip join was fixed in round 1. |
| G23 | Unsure Streamlit returns Scattergeo click events. | Implemented, untested. | Med | Dropdown already required as equal path; Phase 3 browser check. |
| G24 | Detail key: neighborhood or neighborhood+room. | Neighborhood. | Med | Already fixed in round 1. |
| G25 | Streamlit can't switch tabs on row click. | Sets scope + caption. | Med | Spec: row click sets detail scope and shows a caption. |
| G26 | Row highlight with multiple room types. | First row. | Low | Already fixed in round 1 (highlight all rows). |
| G27 | Dropdown placement. | Sidebar. | Low | No change; sidebar placement fits "selection state remains visible". |
| G28 | With a budget, segments with zero within-budget listings disappear from the table. | Followed spec. | Med | Spec: table uses pre-budget `affordability_segments`. |
| G29 | Which n columns to flag. | price_n only. | Low | Spec: flag price_n<30, show others unflagged. |
| G30 | Which Compare deltas hide below n<30; are review deltas wanted. | Hid price/budget only. | Med | Spec: deltas for price, budget share and both review medians; "Not compared (n<30)" by metric denominator. |
| G31 | A == B, and no budget. | Warning; "Set a budget". | Low | Spec: B selector excludes A; "Set a budget". |
| G32 | What Reset covers. | Everything. | Low | Spec: lists all state Reset clears. |
| G33 | Which flags in listing table. | 8 flags. | Low | Spec: lists the 8 flags. |
| G34 | Export page vs all rows. | All rows. | Low | Already fixed in round 1. |
| G35 | Data contract link target; attribution only in contract. | Expander. | Low | Spec: Inside Airbnb CC BY 4.0 notice and contract in an expander. |
| G36 | Hashing 12 MB on every rerun. | Hashed every rerun. | Low | Spec: hash once per path+mtime+size. |
| G37 | No target for uncached filter changes (measured 3.6 s). | Reported. | Med | Spec: uncached filter changes <5 s. |
| G38 | How to force white background. | CSS injection. | Low | Spec: `.streamlit/config.toml` light theme allowed. |
| G39 | Cents outside KPI cards. | Whole dollars. | Low | Spec: all displayed USD whole dollars; exports full precision. |
| G40 | Should the app read `default_*` CSVs? | No. | Low | Spec: they are verification fixtures only. |

## Changes made

| File | Change | Status |
|---|---|---|
| `phase2/clean_data.py` | `exact_float()` correctly rounded parsing for price, reviews_per_month, latitude, longitude in clean and load; flags cast to bool before audit. | Written to your Mac |
| `phase2/backend.py` | `room_type_overview()`; `room_overview` and `room_affordability` added to `dashboard_data()`. | Written (the round 1 session then edited the file again and kept these) |
| `phase2/test_backend.py` | Exact float comparison including coordinates; `test_room_type_kpis_never_pool`. 14 tests pass. | Written (same note) |
| `phase2/DATA_CONTRACT.md` | Float parsing rule, bool audit, `room_type_overview` and new bundle keys. | Written (same note) |
| `BUILD_SPEC.md` | v1.2 edits for Q1 to Q4, G6, G8 to G11, G14 to G17, G19 to G22, G25, G28 to G33, G35 to G40. | **Not applied yet.** The round 1 session changed the spec while I was writing. The edits are saved as `fresh_agent_evidence/round2/BUILD_SPEC.round2.patch`. |

## Acceptance checks

| Check | Result |
|---|---|
| 43,932 rows, unique string IDs | Pass |
| 5,570 / 11 / 11,311 / 30,740 missing; median $224 | Pass |
| Numeric values match the source, including coordinates | Pass after the G2 fix (failed before on 252 coordinates) |
| Rebuild reproduces hashes on another platform | Pass after the G2 fix (failed before) |
| 7 nights includes 7, excludes 8 and unknown | Pass |
| $250 budget numerator/denominator | Pass (3,773 / 15,412) |
| Empty result 0 and N/A | Pass |
| Room type change updates Explore and Details | Pass |
| Hover never changes filters | Not verifiable headlessly |
| Map click selection, offline basemap, mobile layout | Not verifiable headlessly; Phase 3 browser checks |
| Timings | Cold 4.7 to 4.9 s, cached 0.22 s (AppTest, not a laptop browser) |
