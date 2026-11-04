# Los Angeles Airbnb data cleaning

Individual DSO 576 Module 6 submission by Kyi Sin Thant.

Business question: among listings accepting stays of 30 nights or fewer with observed prices, how does median listed nightly price vary by neighborhood and room type?

## Submitted revision

- Branch: `Kyi-branch`
- Branch URL: https://github.com/cynthiaqgao/project/tree/Kyi-branch
- Submitted analysis commit ID: `a01d8667f40870a15079d51939bee5884df42823`
- Analysis commit URL: https://github.com/cynthiaqgao/project/commit/a01d8667f40870a15079d51939bee5884df42823
- Push verified: True

The analysis commit identifies the cleaning package and results. A later documentation commit can attach this literal revision to README without changing analysis. Instructor access must be confirmed separately. The PDF must be uploaded individually to Gradescope after student review.

## Source and version

Inside Airbnb Los Angeles listing data: https://insideairbnb.com/get-the-data/ (CC BY 4.0). Supplied local file `LA_listings.csv`, 43,932 rows and 19 original columns. Source identification comes from the existing project documents. Exact original download/scrape date and upstream transformations are unknown; latest review date is not a scrape date.

SHA-256: `16007ed61afb75ffe44a69e7296bd50a71d61b2cce7cf885eb9d71d1dbd6f289`

`LA_listings.csv` stays unchanged. `clean_airbnb.py` makes `raw_backup/LA_listings.csv` before cleaning and refuses to overwrite a different backup. Both hashes are verified. This source is already tracked in the project repository; the full generated dataset and raw backup are ignored.

## Run

Python 3.10 or newer, from this directory:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python clean_airbnb.py
.venv/bin/python verify_airbnb.py
.venv/bin/python execute_notebook.py
.venv/bin/python build_submission.py
```

Alternatively open `kyi_module_6_hw.ipynb`, select the same environment, restart the kernel and run all cells. The notebook invokes the same cleaning and independent verification scripts. No network download is required to clean the supplied source. Installing dependencies requires package access.

## Rules and expected outputs

All 43,932 listings remain. IDs and licenses are strings; numeric counts use nullable integers; date strings are validated as YYYY-MM-DD. Trim external whitespace (16 names); normalize four N/A license markers. Keep missing values, including 5,570 prices, 30,740 licenses, and 11,311 review rates. No invented price or licensing status is introduced. Hosts can own multiple listings; repeated host IDs are retained. High prices, prices below $10, and stays over 365 nights are flagged and retained. The full decision log and all 14 checklist items are in the PDF.

- `outputs/cleaned_listings.csv`: complete cleaned dataset, ignored by Git; reload with `dtype='string'` for identifier safety or explicitly set identifier string dtypes.
- `outputs/cleaned_sample.csv`: exactly 50 real cleaned rows including difficult cases, tracked.
- `outputs/original_sample.csv`: corresponding original records, tracked.
- `outputs/audit.json`: types, missing counts, failures, flags, hash, row/total reconciliation.
- `outputs/missing_counts.csv`: before/after counts for every original column.
- `outputs/metrics.csv`: market, <=30-night and outlier-sensitivity metrics with denominators.
- `outputs/segment_summary.csv`: neighborhood-room price comparisons for eligible observed-price listings, with metric counts.
- `outputs/record_checks.csv` and `.json`: five distinct original/expected/actual checks and reasons.
- `outputs/verification.json`: independent full-data checks and byte-identical fresh-process rerun of nine output files.
- `outputs/notebook_execution.json`: fresh-kernel execution evidence.
- `output/pdf/Module_6_Airbnb_Cleaning_Kyi.pdf`: individual submission PDF, generated locally and ignored by Git.

## Verification and limitations

`verify_airbnb.py` checks every listing and all three ID columns after serialization, every observed price, null licenses, zero-review missing rates, review/availability totals and every sample row. It starts a separate process from the source and compares nine output files byte for byte. Five distinct records all pass. Codex assisted in preparing these files; programmatic checks do not claim student review.

Median price is the main metric. All-market price n=38,362, mean=$383.14 and median=$224.00. <=30-night price n=34,444 and median=$240.00. Removing 1,634 high-price flags for a separate sensitivity calculation yields mean=$283.93 and median=$213.00, without changing the master dataset.

Calendar availability is not actual occupancy; unavailable nights can be booked or blocked. Review activity is not booking conversion. Missing prices can bias observed-price comparisons. Provided licenses and exemption claims are unverified; missing licenses do not establish noncompliance. The 30-night filter is analytical, not legal. `host_profile_id` meaning is undocumented and it is not substituted for `host_id`. No external merge is performed. Original collection metadata and richer data are needed for temporal, regulatory or booking conclusions.

Method references: https://insideairbnb.com/data-assumptions/ and https://www.airbnb.com/help/article/1634 . Consulted October 2, 2026.

## Phase 3 traveler dashboard (MVP)

**Users and decision.** A traveler planning a Los Angeles stay shortlists neighborhoods and room
types that fit their nightly budget and stay length, compares price and review history, then checks
current listings on Airbnb.

- Live app: _add the Streamlit Community Cloud URL after deployment_
- Demo video: _add the video link_
- Repository: https://github.com/cynthiaqgao/project (branch `Kyi-branch`)

**Pages.** *Explore* (KPI cards per room type, lowest-median-price and budget-fit rankings, price
distribution, neighborhood map, segment table) · *Compare neighborhoods* (two areas, one room type,
same filters) · *Listings & methods* (sortable, paginated listings with Airbnb links, CSV export,
metric definitions).

**Run locally** from this folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If `phase2/outputs/listings.csv` is missing, rebuild it with `python -m phase2.build`; check the
backend with `python -m phase2.test_backend`. Theme settings are in `.streamlit/config.toml`.

**Data scope.** The full Inside Airbnb Los Angeles listing snapshot: 43,932 listings, no sampling
or subsetting. Collection date unknown. 5,570 listings have no price and are excluded from price
statistics, never imputed. Listings above the Q3 + 3×IQR price threshold are kept; a toggle hides them.

**Limitations.** Prices are listed USD/night from one snapshot, not dated quotes or total trip cost.
There are no dates, seasons, bedrooms or ratings, so the app cannot show trends or filter by them.
Review counts are not ratings, and calendar availability is not occupancy. Neighborhood map points
are approximate centers, not boundaries. Rankings hide neighborhoods with fewer than 30 observed
prices (a display rule, not a significance test).
