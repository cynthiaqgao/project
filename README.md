# Los Angeles Airbnb data cleaning

This folder contains Warner0405's individual Module 6 cleaning work. It cleans the Los Angeles summary listings file from Inside Airbnb while preserving one listing per `id`.

## Source and version

- Provider: Inside Airbnb
- Dataset: Los Angeles `listings.csv` summary information and metrics
- Official snapshot path date: 2026-06-15
- Official page: <https://insideairbnb.com/get-the-data/>
- Snapshot file: <https://data.insideairbnb.com/united-states/ca/los-angeles/2026-06-15/visualisations/listings.csv>
- Local source filename: `listings.csv`
- Local file modification date: 2026-09-28
- SHA-256: `d3b34461d0dc409dbe9f99573e3343e342dbcefbb0767b4b62d60b3beb4aceb2`

Do not edit `listings.csv`. If it is absent, download the snapshot above and save it beside `clean_airbnb.py`. The original source file is ignored by Git, while the reproducible cleaned dataset and its validation outputs are published on GitHub for homework review.

## Environment

The submitted run used Python 3.14.7, pandas 3.0.5, and ipykernel 7.3.0. To create a standalone environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The DSO 576 Mac environment can instead run the work directly:

```bash
cd ~/dso576/project/project
~/dso576/00-setup/.venv/bin/python clean_airbnb.py
~/dso576/00-setup/.venv/bin/python verify_airbnb_outputs.py
```

## Notebook procedure

Open `airbnb_cleaning.ipynb` in VS Code, select `~/dso576/00-setup/.venv/bin/python`, choose **Restart Kernel**, and then choose **Run All**. The notebook calls the same functions as the script, recreates every output, and displays the row reconciliation, comparison table, and five record checks.

## Expected outputs

| File | Expected result |
|---|---|
| `outputs/listings_cleaned.csv` | 43,932 cleaned listing rows; published on the homework branch for review. |
| `outputs/listings_cleaned_sample.csv` | 50 deterministic, shareable rows including difficult cases. |
| `outputs/cleaning_summary.json` | Full-data counts, missingness, conversions, flags, denominators, and source hash. |
| `outputs/five_record_checks.csv` | Five original-to-cleaned checks; all should be `True`. |
| `outputs/market_comparison.csv` | 12 neighborhood-group/room-type rows; listing counts sum to 43,932. |

## File guide

- `airbnb_cleaning_rules.md`: rules written before cleaning and the revision log.
- `clean_airbnb.py`: cleaning and output generation.
- `verify_airbnb_outputs.py`: independent assertions over the written outputs.
- `airbnb_cleaning.ipynb`: notebook version of the reproducible workflow.
- `airbnb_cleaning_report.md`: completed Module 6 checklist and evidence.

## Safe sample method

The sample deliberately takes up to five rows from each difficult-case flag, then fills the remaining positions with a deterministic random sample using seed 576. It excludes host names/identifiers, exact coordinates, listing names, and license strings. This reduces unnecessary personal and location detail while retaining the fields needed to inspect the cleaning results.

## GitHub workflow

Work on the individual `Warner` branch. Commit the `.py` files, notebook, rules, report, README, requirements, and all generated files in `outputs/`. Do not add the original `listings.csv`; it is intentionally ignored because the documented public source can be downloaded when the workflow is reproduced. The team can later reconcile each member's branch into the group checklist.
