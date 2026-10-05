# Los Angeles Airbnb listing cleaning

Data source: Inside Airbnb, Los Angeles listings.
Input: LA_listings.csv (43,932 rows, 19 columns).
Branch: cleaning-yaxin.

Run from the project folder:
uv run --with pandas python clean_listings_yaxin.py

The script reports missing prices, duplicate IDs, price range, median price, high prices, missing neighborhoods, and invalid availability. It creates LA_listings_cleaned_yaxin.csv locally and LA_listings_sample_yaxin.csv with 50 rows. The sample includes five manually checked records first (IDs 2708, 2732, 6033, 9140, 584724), including a missing-price case and a price above $1,000; remaining rows come from the start of the cleaned dataset, with duplicate IDs removed.

Cleaning decisions: Keep all original listings. Add has_price to mark missing prices and high_price_review to mark prices above $1,000 for further review.
Branch URL: https://github.com/cynthiaqgao/project/tree/cleaning-yaxin
Cleaning code commit: 1401be80d19605f996037e5dfe5e3ac0a30d6951
Data version: LA_listings.csv in the team's Phase 1 repository (43,932 rows, 19 columns); original download date not recorded.