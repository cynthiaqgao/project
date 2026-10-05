import pandas as pd

raw = pd.read_csv("LA_listings.csv")
print(raw.shape)
print("Missing price:", raw["price"].isna().sum())
print("Duplicate IDs:", raw["id"].duplicated().sum())
print("Price range:", raw["price"].min(), raw["price"].max())
print("Median price:", raw["price"].median())
print("Listings above $1000:", (raw["price"] > 1000).sum())
print("Missing neighborhoods:", raw["neighbourhood"].isna().sum())

cleaned = raw.copy()
cleaned["has_price"] = cleaned["price"].notna()
print("Price flags:", cleaned["has_price"].value_counts())
cleaned["high_price_review"] = cleaned["price"] > 1000
print("High price flags:", cleaned["high_price_review"].value_counts())
print("Invalid availability:", ((raw["availability_365"] < 0) | (raw["availability_365"] > 365)).sum())
cleaned.to_csv("LA_listings_cleaned_yaxin.csv", index=False)
cleaned.head(50).to_csv("LA_listings_sample_yaxin.csv", index=False)
