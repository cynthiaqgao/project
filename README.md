# DSO 576 HW 6 — Los Angeles Airbnb Data Cleaning

This branch contains Cynthia Gao's HW 6 data-cleaning script for a Los Angeles short-term-rental dataset. The script preserves the raw data in memory, standardizes selected fields, investigates missing and duplicate records, flags suspicious values, reconciles before/after totals, and verifies representative records.

Github Branch: Cynthia_branch

https://github.com/cynthiaqgao/project/tree/Cynthia_branch

Github Commit ID: cfc3fe91ce8a92e5579c4145adcd76d47d1b9385

## Data source and version

- **Source:** [Inside Airbnb — Get the Data](https://insideairbnb.com/get-the-data/)
- **Market/table:** Los Angeles `listings.csv`; one row represents one Airbnb listing.
- **Snapshot date:** June 15, 2026.
- **Download date:** September 21, 2026.
- **Local filename:** `LA_listings.csv`
- **Shape when loaded by pandas:** 43,932 rows and 19 columns.
- **SHA-256:** `16007ed61afb75ffe44a69e7296bd50a71d61b2cce7cf885eb9d71d1dbd6f289`

The snapshot is cross-sectional rather than a time series. It includes listing and host identifiers, neighborhood, coordinates, room type, price, minimum stay, review activity, availability, and license information. Inside Airbnb is an independent project and is not affiliated with Airbnb.

## Files

- `cynthia_hw6.py` — cleaning, validation, and reconciliation workflow.
- `LA_listings.csv` — raw source data used by the script.

The script does not overwrite the source CSV or write a cleaned CSV. It keeps the cleaned DataFrame in memory and prints its checks and summaries to the terminal.

## Run instructions

Python 3.11 or later and pandas are required. The current version was verified with Python 3.12.1 and pandas 3.0.5.

From the project directory, create an optional virtual environment, install pandas, and run the script:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pandas
python3 cynthia_hw6.py
```

`cynthia_hw6.py` currently sets `DATA_PATH` to:

```text
/Users/cynthiagao/dso576/project/LA_listings.csv
```

If the repository is stored elsewhere, update `DATA_PATH` near the top of the script before running it. A successful run exits without an assertion error and prints the results described below.

## Expected output

The output begins with a five-row preview, the dataset shape `(43932, 19)`, the first listing, and a column-level summary of data types, missing values, and unique values. It then prints cleaning comparisons, duplicate checks, missing-data checks, suspicious-value diagnostics, extreme records, reconciliation totals, metric denominators, and seven record-level validation checks.

Key expected results are:

| Check | Expected result |
|---|---:|
| Starting/final rows | 43,932 / 43,932 |
| Columns before/after | 19 / 28 |
| IDs removed/added | 0 / 0 |
| Exact duplicate rows | 0 |
| Repeated listing IDs | 0 |
| Possible duplicate-group rows | 224 |
| Extra possible duplicate rows | 147 |
| Missing `reviews_per_month` values filled with `0` | 11,311 |
| Missing prices retained | 5,570 (12.7%) |
| Missing licenses retained | 30,740 (70.0%) |
| Rows with at least one unusual-value flag | 823 |
| Median/mean price among priced listings | $224.00 / $383.14 |
| Total reviews | 1,856,294 |
| Reviews in the last 12 months | 377,493 |
| Listings with a license | 13,192 (30.03%) |

Text cleaning changes 1,070 listing names, 257 host names, and 148 license values. It removes hidden formatting characters and excess whitespace and uppercases license codes that match the code pattern. As a result, distinct listing names decrease from 42,715 to 42,707 and distinct license values decrease from 7,718 to 7,691.

All impossible-value checks should return `0` except `ltm > 0 but last review > 1 yr old`, which returns `34`. The generated flags should total:

```text
flag_price_high             385
flag_price_low              371
flag_min_nights_gt_365       24
flag_reviews_extreme         44
flag_host_count_mismatch      0
```

The final record-validation table should contain seven rows and show `True` in the `match` column for every row. The reconciliation assertion at the end of the row-count section should also pass.

Some printed tables are intentionally long because they expose the records behind duplicate and outlier checks for manual review.
