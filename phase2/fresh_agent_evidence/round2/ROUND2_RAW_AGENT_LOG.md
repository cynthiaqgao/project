# Fresh-agent build log: Phase 3 dashboard MVP

Agent: an independent coding agent working from a clean checkout of `/home/claude/fresh_repo`. Its only instruction was "Read BUILD_SPEC.md and build the Phase 3 dashboard MVP". No human answered questions. Date: 2026-10-16.
Environment: Python 3.13.16, pandas 2.3.3, numpy 2.5.3, streamlit 1.66.0, plotly 7.1.0. The plain `python` command also exists.

## 1. Summary

**What I built.** I added these files and changed nothing in BUILD_SPEC.md, phase2 source, or LA_listings.csv:
- `app.py` is the Streamlit entry point. It holds the sidebar controls, Reset, the detail-selection dropdown, the snapshot caveat, the active-filter line, the empty state, and three tabs. Data loading is cached with `st.cache_data` keyed on the canonical file's SHA-256. Aggregations are cached on that SHA plus a normalized `Filters` tuple, and the cache is cleared when the hash changes. Every metric comes from `phase2.backend`.
- `views/explore.py` renders:
  - the 4-card KPI row
  - per-room price bars and affordability bars (top 15, Viridis colors, n ≥ 30 rule, ranked with `rank_market_segments`)
  - a pre-budget step CDF with a log-x toggle and a budget line
  - per-room `Scattergeo` neighborhood markers (marker area proportional to count, gray for missing values, a 3-size count legend, disclosure of omitted map_n, and a "Coordinate grid (offline)" fallback)
  - the segment evidence table, with search, the pre-budget columns joined one-to-one, n<30 flags, row click to set detail, and the selected row pre-highlighted
- `views/compare.py` compares A and B with independent selectors (defaults Hollywood, Venice, Entire home/apt). It calls `compare_neighbourhoods` and shows A−B in USD, the budget share difference in percentage points, and A/B−1 only when B>0. It does not declare a winner when n<30. It also draws a median + IQR bar chart.
- `views/details.py` shows listing evidence: price ascending with nulls last and id as tie-breaker, 50 per page, a "Check current details" Airbnb link, data flags, and a CSV download with quoted string IDs. It also renders the Methods section from `audit.json`, the canonical SHA, active filters, definitions, caveats, the outlier threshold, and the data contract.
- `views/common.py` holds formatting helpers and constants only. `views/__init__.py` is new.

**Commands run, with results:**

| Command | Result |
|---|---|
| `python -m pip install -r phase2/requirements.txt` | OK. pandas only, already satisfied. Streamlit and Plotly are not pinned anywhere. |
| `python -m phase2.build` | OK (~9 s). Wrote 18 output files. It also **modified the committed `phase2/outputs/listings.csv`** (252 rows differ in coordinate float text) and `manifest.json` (hashes changed for listings.csv and the 4 `*_map.csv`). See G2. |
| `python -m phase2.test_backend` (after build) | 10/10 passed (~14 s). `verification.json` regenerated. |
| `python -m phase2.test_backend` in a fresh `git clone` **without** running the build first | **1 error**: `test_fresh_process_rebuild` fails with FileNotFoundError on `budget250_affordability.csv`. The `default_*` and `budget250_*` CSVs are not committed. Note also that `LA_listings.csv` is not git-tracked, so I had to copy it in. |
| `python3 -c "import app"` and imports of every `views.*` module | OK |
| `streamlit run app.py --server.headless true` | Server starts and `/_stcore/health` returns `ok`, `/` returns 200. No browser was available, so nothing was rendered visually. |
| `streamlit.testing.v1.AppTest` scenarios | 0 exceptions in every scenario: default; $250 budget; empty neighborhoods; Reset from empty state; All stay lengths; Compare (default, same area, Shared room with small n); 2 room types; 0 room types; detail = Venice; exclude high prices; min reviews 5; log-x; grid map; map within-budget metric; sidebar Reset. |
| Edge-case harness (`AppTest.from_file` on a scratch script) | Coordinates nulled for Venice gives "Omitted from map: 1 segment(s), 442 listing(s)". All-missing Hollywood prices give a gray marker. Empty distribution shows the info message and no CDF. The CSV export quotes IDs. |

**Key results**
- Default view: 16,633 matching listings, median $371, budget card shows "Set a budget", 88.9% reviewed.
- $250 budget: 3,773 matching, median $194, **24.5% (3,773 of 15,412 pre-budget priced)**. This matches `budget250_affordability.csv` and `budget250_overview.csv`.
- Empty neighborhood selection: 0 listings, N/A elsewhere, "No listings match these filters" with a Reset button.
- All stay lengths: 32,454 listings.
- Timings (AppTest harness, not a browser): cold first run 4.7–4.9 s; uncached filter change ~3.6 s; cached filter change ~0.22 s.

## 2. Questions (Q) and guesses (G)

| ID | Spec section | What was unclear | What I assumed/did | Impact | Suggested spec fix |
|---|---|---|---|---|---|
| Q1 | §1 U3 | "add the neighborhood to a shortlist". No shortlist feature, control or state is specified in §2/§4. | Built no shortlist. The only selection is the single detail neighborhood. | High | Either specify a shortlist (control, storage, where it is shown and exported) or reword U3 to "set it as the detail neighborhood". |
| Q2 | §7 step 2 | "Confirm team cleaning resolutions and merge … into main" | An agent can't do this. Skipped and not claimed. | Med | Mark step 2 as a human/team gate outside the agent build order. |
| Q3 | §7 step 5 | "test … network fallback". No pass criterion. Plotly `Scattergeo` loads its topojson outline from a CDN, and an outline failure can't be detected from Python. | Added a manual "Map display: Coordinate grid (offline)" radio that shows the same markers on a lon/lat grid. Offline behavior was **not tested**. | Med | State the expected fallback mechanism (manual toggle vs. automatic) and how to test it, e.g. "with network disabled, grid mode shows all markers". |
| Q4 | §5 / §7.7 | "At 1280×800 and 375px … no clipped legends", "mobile layout". No headless way to verify was given. | Relied on Streamlit column stacking and horizontal legends below plots. **Not verified.** | Med | Name the tool and procedure for viewport checks (e.g. Playwright screenshots) and what counts as a pass. |
| G1 | §6, §7.1, README | "Requirements are in phase2/requirements.txt", but that file only pins pandas. README says to install Streamlit/Plotly "when implementing" and record versions. §6 mentions "existing root requirements", which do not exist. | Used the preinstalled streamlit 1.66.0 and plotly 7.1.0. Created no requirements file, since the task limited me to app.py and views/. | Med | Add a Phase 3 requirements file with pinned streamlit/plotly versions, or say which file to create. Remove the root-requirements sentence. |
| G2 | §6, §7.1, DATA_CONTRACT | "manifest pins source/output hashes" and the build is meant to be reproducible. On this environment the build **rewrites committed listings.csv**: 252 lines differ in coordinate text, e.g. `34.094219852620036` → `34.09421985262004`. The manifest hashes for listings.csv, default_map, default_affordability_map, budget250_map and budget250_affordability_map also change. Tests still pass because they compare against the freshly regenerated manifest. | Kept the regenerated outputs, as the task allows. The app loads whatever canonical file is present and keys the cache on its hash. | High | Write floats with a fixed format (e.g. `float_format='%.17g'` or keep the source strings), or pin the numpy/pandas/Python versions. Make the test compare against the **committed** manifest instead of one it just rewrote. |
| G3 | §7.1, README | README lists `outputs/default_*.csv`, `budget250_*.csv` and `example_comparison.csv` as present, and `.gitignore` has an exception for them, but they are not committed. A test in a clean clone fails until the build runs. | Ran build before tests, following the §7 order. | Med | Commit the outputs, or state "tests require running build first". |
| G4 | README, RECONCILIATION | RECONCILIATION says "Existing raw source is already tracked", but `LA_listings.csv` is **not tracked** (`*.csv` is ignored). A `git clone` has no source, so the build fails. | Used the file in the provided working tree. | Med | Track `LA_listings.csv` (add a `!LA_listings.csv` exception) or document how to obtain it and its expected SHA. |
| G5 | README | README references a notebook (`phase2_traveler_clean_team_data.ipynb`), `requirements-notebook.txt`, `python -m phase2.execute_notebook` and `../.venv/bin/python`. None exist. | Ignored them. | Low | Remove the references or add the files. Avoid machine-relative venv paths. |
| G6 | §7 concrete checks | "All observed numeric values … match the source." This holds with pandas' default float parser, which the test uses. Exact text and Python `float()` round-trip do not hold: source `-118.25124977495697` is canonical `…696`, and `float('34.094219852620036') != float('34.09421985262004')`. The test also does not check latitude/longitude. | Reported as passing under the backend's own definition, with this caveat. | Med | Define "match": parse with `float_precision='round_trip'`, or keep source strings. Add lat/long to the test. |
| G7 | DATA_CONTRACT derived columns | "All flags are nonnullable bool", but `audit.json` dtypes list several flags as `boolean` (nullable). | No change. `load_listings` returns plain bool. | Low | Cast to bool before the audit, or document the difference. |
| G8 | §2 | "neighborhood multiselect (all initially …)" with 265 neighborhoods means 265 chips by default. | Pre-filled all 265. If the selection equals all, `Filters.neighbourhoods=None`; if empty, `()`. | Low | Allow an "All neighborhoods" checkbox, or confirm the full pre-filled multiselect. |
| G9 | §2 | "optional positive USD nightly budget". The widget form is unspecified. | `number_input`, empty means no budget, min 0.01, step 10, no maximum. | Low | Specify the widget, step and minimum, or accept any positive value. |
| G10 | §2 | "clearly labeled All stay lengths option". The form is unspecified. | Checkbox "All stay lengths (includes unknown minimum stays)". When checked, the nights input is disabled and keeps its value. | Low | Specify checkbox vs. a radio item vs. a select option. |
| G11 | §2, §4 | "Global sidebar controls apply immediately to all Explore views". Compare "inherits" some globals. The Details tab population is not stated. | The listing table uses the global selected (budget-filtered) `listings`, scoped to the detail neighborhood. Compare uses the globals except neighborhoods and room type. | Low | State which tabs each global control affects. |
| G12 | §5/§7 vs §4 Compare | "Changing room type must change all relevant views", but Compare has its own room-type selector defaulting to Entire home/apt. | The global room type does **not** change Compare. | Med | Say explicitly that Compare is excluded, or make Compare's room type inherit the global one when exactly one is selected. |
| G13 | §2, §4 KPI | "Global listing counts can summarize multiple room types only with a visible 'Mixed room types' label", and "Never pool room types for a ranking or comparison". It is unclear whether the **median price** and **reviewed share** KPI cards may pool room types. `overview` pools them. | Kept all 4 cards pooled from `overview`, with a visible "Mixed room types" caption when more than one room type is selected. | High | State per card whether pooled medians are allowed, or require per-room KPI rows when several room types are selected. |
| G14 | §3/§4 KPI | The median-price KPI uses the budget-filtered population, so with a budget it is always ≤ budget ($194 vs. $371 pre-budget at $250). The spec is explicit, but a traveler could misread it. | Followed the spec. The caption shows price_n, and the budget card is labeled "pre-budget". | Med | Confirm the intent, or show both "within your budget" and "all priced" medians. |
| G15 | §4 price bars | "Use selected segments" plus n≥30. With $250, only 30 of 229 Entire-home segments qualify. The ranking becomes "lowest median among within-budget listings". | Followed the spec and added a caption giving the excluded count. | Med | Confirm whether price ranking should use the pre-budget population when a budget is set. |
| G16 | §4/§5 | "same shared 0-to-maximum scale across room panels". The maximum is not defined. | Color: cmin 0, cmax = largest median among displayed bars across room panels. X axis: 0 to 1.15×max (headroom for labels). | Low | Define the maximum (displayed bars vs. all segments vs. Q3). |
| G17 | §4 price/affordability | "top 15 … per room type". The panel layout is unspecified. | One chart per room type, stacked vertically. | Low | Specify facets vs. separate charts. |
| G18 | §4 CDF | "Default x limit is full observed range". The maximum is $20,583, which squashes the curve. | Kept the full range. Added a log-x toggle (off by default). | Low | Consider allowing a default clip at the high-price threshold, with a label. |
| G19 | §4 map | "enable pan/zoom and scale bar where the map component supports it". Plotly `Scattergeo` has no scale bar. | No scale bar. Pan/zoom is enabled (scrollZoom, dragmode pan). Graticule at 0.25°. | Low | Drop the scale bar or name a component that has one. |
| G20 | §4 map | "3-symbol count legend". The values are not given. | Distinct listing_count values at the 10th percentile, median and maximum, drawn as hollow legend markers with the same sizeref. Legend marker sizes were not verified visually. | Low | Specify fixed legend counts (e.g. 10/100/1,000). |
| G21 | §4 map | The color metric selector, its label and its default are unspecified. | Radio "Map color metric": median price (selected, default) or within-budget share (pre-budget, only offered when a budget is set). | Low | Name the control and its default. |
| G22 | §4 map hover | "Use `map` for selected price … `affordability_map` for pre-budget budget evidence". With a budget, the `map` price view only contains segments that have at least one within-budget listing, but hover must show the budget numerator/denominator. | Merged `within_budget_n`/`price_n` from `affordability_map` into the hover, labeled pre-budget. In the price view, segments with no within-budget listing get no marker. | Med | Say which marker set to show in price mode when a budget is on (the selected or the pre-budget segments). |
| G23 | §4 map click | "Click sets selected neighborhood". I don't know whether Streamlit's `on_select` returns point clicks for `Scattergeo`. | Implemented an `on_select` callback that reads `customdata[0]`. An empty selection returns to global scope. **Not verifiable headlessly.** The keyboard dropdown gives the same behavior and was tested. | Med | Note the required Streamlit version or capability, or accept the dropdown as the primary path. |
| G24 | §1 U4, §4 | "Neighborhood/room row … opens details" vs. "Click sets selected **neighborhood**". It is unclear whether the detail scope is the neighborhood or the neighborhood+room pair. | Detail scope is the neighborhood only. The listing table shows every selected room type in it. | Med | Define the detail key (neighborhood or neighborhood+room). |
| G25 | §4 | "Row click opens details". Streamlit can't switch tabs programmatically. | A row click sets the detail scope. The user opens the "Listing details & methods" tab, and a caption says so. | Med | Accept "sets detail scope", or put details under the table in Explore. |
| G26 | §4 | "highlights its table row" | Uses the `st.dataframe` `selection_default` on the first row of that neighborhood. With several room types, only one row is highlighted. | Low | Specify the highlight style and the multi-row case. |
| G27 | §4, §5 | Where the "keyboard-accessible neighborhood dropdown" goes. "All … selection state remain visible." | Put it in the sidebar under "Detail selection" so it is visible on every tab. | Low | Specify placement. |
| G28 | §4 segment table | "Show all segments" vs. the table being built from **selected** segments. With a budget, segments with zero within-budget listings disappear (229 shown vs. 259 pre-budget segments). | Followed "selected segments", with a one-to-one left join from `affordability_segments`. | Med | Say whether pre-budget-only segments should appear, e.g. with 0 selected listings. |
| G29 | §4 segment table | "searchable/sortable", "flag metric n<30" | Built-in header sort plus a neighborhood text search box. Only `price_n<30` is flagged. Review/availability n is shown but not flagged. The selected-population `within_budget_*` columns were dropped (always 100% or None) and replaced with the pre-budget join. | Low | List which n columns are flagged and which columns appear. |
| G30 | §4 Compare | "no numeric 'winner' for either comparison group below the metric's threshold" | When either side has price_n<30, the price A−B and A/B−1 and the budget-share pp difference show "Not compared (n<30)". Raw values still appear. No review deltas are shown at all, since the spec lists only price and budget-share deltas. | Med | State exactly which deltas are hidden or shown below the threshold, and whether review deltas are wanted. |
| G31 | §4 Compare | Behavior when A == B, or when there is no budget | A == B shows a warning instead of a table. No budget shows "Set a budget" in the budget rows. | Low | Specify both. |
| G32 | §2, §5 | "Reset restores these defaults / clears detail selection". It is unclear whether Compare selectors, map metric/mode, log toggle, search and page are included. | Reset restores all of them too. | Low | List exactly the state Reset covers. |
| G33 | §4 listing evidence | "…and flags". Which flags is not stated. | Shown as a text column: price missing, min stay unknown, high-price flag, price < $10, min stay > 365, both review-inconsistency flags, coordinates screened. license_missing is excluded. | Low | Enumerate the flags to display. |
| G34 | §4 listing evidence | "Download exports the filtered displayed columns". It is unclear whether that means the current page or all pages. | All filtered rows (every page), displayed columns only, `QUOTE_NONNUMERIC`, so IDs and other strings are quoted. | Low | Specify the page vs. full export. |
| G35 | §4 Methods | "link to data contract". No URL exists. Attribution and CC BY 4.0 appear only in DATA_CONTRACT. | Showed the repo path plus an expander rendering `phase2/DATA_CONTRACT.md`. Added the Inside Airbnb CC BY 4.0 line. Counts come from `audit.json`, read by the app (the backend stays file-free). | Low | Give the link target and put the attribution requirement in BUILD_SPEC. |
| G36 | §6 caching | "cache canonical loading by canonical file SHA-256 … Clear cache when hash changes" | SHA-256 of the 12 MB file is computed on every rerun. The Filters tuple is normalized by sorting neighborhoods and room types. `st.cache_data.clear()` runs when the session's stored hash differs. | Low | State whether hashing on every rerun is acceptable, or use mtime+size. |
| G37 | §6 performance | "Profile on the developer laptop: cold load <5s, cached filter changes <1s". This was a container with AppTest, not a browser. | Cold 4.7–4.9 s (borderline). Cached rerun ~0.22 s. **Uncached** first-time filter change ~3.6 s, which has no target. | Med | Define the measurement method and add a target for uncached filter changes. |
| G38 | §5 | "White background" | Forced `.stApp` background to white with injected CSS. No `.streamlit/config.toml` was added (outside the allowed files). | Low | Allow or require `.streamlit/config.toml` with a light theme. |
| G39 | §5 | "KPI prices show whole USD" | All USD shown as whole dollars, including the table and compare. Q1 of 93.5 displays as $94. | Low | Say whether non-KPI tables may show cents. |
| G40 | Header vs. §7 | "Phase 2 build contract v1.0. Build the Phase 3 MVP". It also says to use "only what is in the repository". `build.py` is described as producing "representative dashboard tables". | The app never reads `default_*`/`budget250_*` CSVs. It recomputes from the canonical CSV through the backend and uses the exports only for verification. | Low | State that the exported tables are fixtures, not app inputs. |

## 3. Spec acceptance checks

**Concrete data checks (§7)**

| Check | Status | Evidence |
|---|---|---|
| Canonical rows 43,932 with unique string IDs | **Passed** | `load_listings()`: 43,932 rows, `id` dtype string, unique |
| 5,570 prices / 11 min stays / 11,311 monthly rates / 30,740 licenses missing | **Passed** | Backend counts and audit.json |
| Full-market median observed price $224 | **Passed** | `d.price.median() == 224.0` |
| All observed numeric values and ID digits match the source | **Passed with caveat** | IDs exact. Numerics are equal under the pandas default parser. Exact text/round-trip differs for some coordinates, and lat/long are not covered by the test (G6). |
| 7-night stay includes minimum_nights=7 and excludes 8/unknown | **Passed** | Filtered max = 7, a 7 is present, no unknowns. Unit test `test_exact_stay_boundary…` also passed. |
| $250 budget: numerator = selected priced listings; denominator = pre-budget price_n | **Passed** | Entire home 3,773/15,412; all rooms 7,703/20,410; Private room 3,750/4,535. The app card shows "3,773 of 15,412", matching `budget250_*.csv`. |
| Empty result count=0, median=N/A | **Passed** | Backend NaN median. App shows 0 and "N/A". |
| Changing room type changes all relevant views | **Passed for Explore/Details** | Every `dashboard_data` table differs between Entire home and Private room. Compare is intentionally independent (G12). |
| Hovering never changes filters | **Not verifiable** | Hover isn't simulated in AppTest. By construction, only `on_select` callbacks change detail state and never filters. |

**Build-order checks (§7.1–7.7)**

| Check | Status |
|---|---|
| Build + test commands run as documented | **Passed with caveats**: they pass only when run in order (G3). The build rewrites committed outputs in this environment (G2). The source is untracked (G4). |
| Team merge to main (step 2) | **Not verifiable / not performed** (Q2) |
| Global controls, KPI row, segment table (step 3) | **Passed** (AppTest, 0 exceptions) |
| Price/affordability bars, step CDF, selected vs. pre-budget counts incl. budget250 (step 4) | **Passed** for data, chart specs (x 0–max USD, 0–105% for shares, Viridis, `line_shape='hv'`) and budget250 numbers. Visual appearance **not verified**. |
| Geographic markers, hover, detail selection, keyboard equivalent (step 5) | **Partly passed**: markers, omitted-coordinate disclosure, gray missing-price markers, small groups and the dropdown were tested. Click selection on Scattergeo and the network fallback are **not verified** (G23, Q3). |
| Same-room comparison, pagination, export (step 6) | **Passed**: compare table and n<30 suppression, A == B guard, 50-row pages, CSV with quoted IDs |
| Empty results | **Passed** (empty neighborhoods and empty room types) |
| All missing prices | **Passed** (synthetic: gray marker, N/A median, no CDF when price_n=0) |
| Minimum stay exactly equal to trip length | **Passed** (backend) |
| 0 reviews vs. missing rates | **Passed** (backend test: never-reviewed rates stay null; app shows rate n separately) |
| Outlier toggle | **Passed** (32,454 to 30,898 listings under All stay lengths; runs without errors) |
| Reset | **Passed** (from the empty state and from the sidebar: nights 7, all-stays off, detail = global) |
| Shared scales | **Passed by construction** (shared cmax/x-range across room panels, 0–100% for shares). Visual check not performed. |
| Mobile layout / 1280×800 / no clipped legends | **Not verifiable** (Q4) |
| Clean environment startup | **Partly passed**: `streamlit run` health OK in this environment. A clean `git clone` lacks LA_listings.csv, and there are no pinned UI requirements (G1, G4). |
| Response timings (cold <5 s, cached <1 s) | **Passed, borderline**: cold 4.7–4.9 s and cached 0.22 s in the AppTest harness. Not measured in a browser on a laptop (G37). |
| §5 rules: titles name metric/population/unit, no false zeros, n≥30 display rule, empty-state message with Reset | **Passed** by AppTest output and chart-spec inspection |
| Fresh-agent build check | **Performed (this log)**. Contract fixes are not applied: BUILD_SPEC was not to be edited. |
