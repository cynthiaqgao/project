from pathlib import Path
import pandas as pd
from phase2.backend import Filters, filter_listings, overview_metrics

root = Path(__file__).resolve().parent

d = pd.read_csv(
    root / "phase2/outputs/listings.csv",
    dtype={
        "id": "string",
        "minimum_nights": "Int64",
        "number_of_reviews": "Int64",
    },
)

# Check 1: default seven-night filter
selected = filter_listings(d, Filters())

direct = d.loc[
    (d.room_type == "Entire home/apt")
    & d.minimum_nights.le(7).fillna(False)
]

assert set(selected.id) == set(direct.id)

positive = int(
    direct.number_of_reviews.gt(0).fillna(False).sum()
)
actual = overview_metrics(selected).iloc[0].reviewed_share

print("Total listings:", len(d))
print("Selected listings:", len(selected))
print("Listings with reviews:", positive)
print("Direct reviewed share:", positive / len(direct))
print("Backend reviewed share:", actual)
print("Missing review counts:", int(d.number_of_reviews.isna().sum()))

# Check 2: minimum-stay boundary
case = d.head(3).copy().reset_index(drop=True)
case["room_type"] = "Entire home/apt"
case["minimum_nights"] = pd.Series(
    [7, 8, pd.NA], dtype="Int64"
)

print(
    "Boundary selected indexes:",
    filter_listings(case, Filters()).index.tolist(),
)

# Check 3: missing-review denominator
case["number_of_reviews"] = pd.Series(
    [1, pd.NA, 0], dtype="Int64"
)

print("Missing-review case expected:", 1 / 3)
print(
    "Missing-review case actual:",
    overview_metrics(case).iloc[0].reviewed_share,
)