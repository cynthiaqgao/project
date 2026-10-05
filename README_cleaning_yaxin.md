# Los Angeles Airbnb listing cleaning

Data source: Inside Airbnb, Los Angeles listings.
Input: LA_listings.csv (43,932 rows, 19 columns).
Branch: cleaning-yaxin.

Run from the project folder:
uv run --with pandas python clean_listings_yaxin.py

The script reports missing prices, duplicate IDs, price range, median price, high prices, missing neighborhoods, and invalid availability. It creates LA_listings_cleaned_yaxin.csv locally and LA_listings_sample_yaxin.csv with 50 rows.

Cleaning decisions: Keep all original listings. Add has_price to mark missing prices and high_price_review to mark prices above $1,000 for further review.