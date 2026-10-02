# Los Angeles Airbnb Listings: Data Cleaning

## Project purpose

This project prepares Los Angeles Airbnb listings for analysis of neighborhood and room-type segments with low recent review activity and high annual availability. Median listing price will also be compared across segments.

`number_of_reviews_ltm` and `availability_365` are indirect measures of marketplace activity. They do not directly measure bookings or occupancy. Availability can also be affected by host decisions.

## Data source

- Source: [Inside Airbnb — Get the Data](https://insideairbnb.com/get-the-data/)
- File: `LA_listings.csv`
- Snapshot date: **[Enter the snapshot date shown for the downloaded Los Angeles file.]**
- Download date: **[Enter the date you downloaded the file, if known.]**

The original CSV is kept unchanged.

## Cleaning decisions

- Read `id`, `host_id`, and `host_profile_id` as strings to preserve identifiers.
- Trim leading and trailing whitespace from `name`; preserve the wording, capitalization, punctuation, and internal spaces.
- Convert `last_review` to a datetime column.
- Convert `minimum_nights` and `calculated_host_listings_count` to nullable integer columns.
- Preserve missing values; do not impute or drop rows.
- Keep all 43,932 records. No repeated listing IDs or exact duplicate rows were found.
- Create a reproducible sample of up to 50 cleaned rows, including examples of difficult cases.

Only one listings file is used, so no data merges are applicable.

## Files

- `LA_listings.csv` — original source data
- `clean_listings.py` — reproducible cleaning script
- `module6_cleaning.ipynb` — inspection, cleaning decisions, and validation
- `cleaned_sample.csv` — up to 50 cleaned records
- `requirements.txt` — Python package dependency

## Run the cleaning script

From this folder, install the dependency and run the script:

```bash
python -m pip install -r requirements.txt
python clean_listings.py