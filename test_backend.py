"""Lightweight checks for the Phase 2 backend functions."""

import pandas as pd

from cleaning import (
    clean_listings,
    filter_listings,
    market_summary,
    overview_metrics,
    rank_market_segments,
)


raw_df = pd.read_csv("LA_listings.csv")
clean_df = clean_listings(raw_df)

assert len(raw_df) == 43_932
assert len(clean_df) == 38_353
assert clean_df["id"].is_unique
assert clean_df["price"].notna().all()
assert clean_df["minimum_nights"].notna().all()
assert clean_df["reviews_per_month"].notna().all()

summary_df = market_summary(clean_df)
assert len(summary_df) == 592
assert set(summary_df.columns) == {
    "neighbourhood",
    "room_type",
    "listing_count",
    "median_price",
    "average_available_nights",
    "average_reviews_per_month",
}

filtered_df = filter_listings(
    clean_df,
    neighbourhoods=["Hollywood"],
    room_types=["Entire home/apt"],
)
assert len(filtered_df) == 1_030

overview_df = overview_metrics(filtered_df)
assert overview_df.loc[0, "listing_count"] == 1_030

ranked_df = rank_market_segments(summary_df, min_listings=30)
assert ranked_df.loc[0, "rank"] == 1
assert ranked_df["listing_count"].ge(30).all()
assert ranked_df["listing_count"].is_monotonic_decreasing

print("All backend checks passed.")
