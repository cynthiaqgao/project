import pandas as pd

# Make printed tables readable when running as a script
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------
# Load the data and keep an untouched copy
# ---------------------------------------------------------------
DATA_PATH = "/Users/cynthiagao/dso576/project/LA_listings.csv"

df = pd.read_csv(DATA_PATH)
raw = df.copy()  # original data, never modified

print(df.head())
print(df.shape)

# One row = one listing; show the first record
print(df.iloc[[0]])

# ---------------------------------------------------------------
# Inspect columns and types
# ---------------------------------------------------------------
dtype_summary = pd.DataFrame({
    "dtype": df.dtypes,
    "nulls": df.isna().sum(),
    "n_unique": df.nunique(),
})
print(dtype_summary)

# Fix types: last_review to datetime, label columns to category
df["last_review"] = pd.to_datetime(df["last_review"])

for c in ["room_type", "neighbourhood_group", "neighbourhood"]:
    df[c] = df[c].astype("category")

# ---------------------------------------------------------------
# Standardize text
# ---------------------------------------------------------------
INVISIBLE = r"[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]"


def clean_text(s):
    return (s.str.replace(INVISIBLE, "", regex=True)   # hidden formatting characters
             .str.replace(r"\s+", " ", regex=True)     # spaces/tabs/newlines -> one space
             .str.strip())


text_cols = ["name", "host_name", "neighbourhood_group",
             "neighbourhood", "room_type", "license"]

for c in text_cols:
    df[c] = clean_text(df[c].astype("string"))

# Uppercase license codes only (leaves free-text licenses alone)
is_code = df["license"].str.fullmatch(r"[A-Za-z]{2,5}\d{2}-\d{3,6}", na=False)
df.loc[is_code, "license"] = df.loc[is_code, "license"].str.upper()

# Before/after check for the columns that changed
for c in ["name", "host_name", "license"]:
    changed = raw[c].fillna("") != df[c].fillna("")
    print(c, "rows changed:", changed.sum())
    print(pd.DataFrame({"before": raw.loc[changed, c].map(repr),
                        "after": df.loc[changed, c].map(repr)}).head(5))

# ---------------------------------------------------------------
# Investigate duplicates
# ---------------------------------------------------------------
# 1. Exact duplicate rows: every column identical
print("Rows involved in exact duplicates:", df.duplicated(keep=False).sum())
print("Extra copies (would be removed):", df.duplicated().sum())

# 2. Repeated IDs: same listing id appearing more than once
id_dups = df["id"].duplicated(keep=False)
print("Rows with a repeated id:", id_dups.sum())
print("Distinct ids that repeat:", df.loc[id_dups, "id"].nunique())

# 3. Possible duplicate listings: different ids, same host, name, and location
key = ["host_id", "name", "latitude", "longitude"]
near_dups = df.duplicated(subset=key, keep=False) & df["host_id"].notna()
print("Rows in possible duplicate groups:", near_dups.sum())
print("Extra rows beyond the first in each group:",
      (df.duplicated(subset=key) & df["host_id"].notna()).sum())

# Look at the possible duplicates side by side
cols = ["id", "host_id", "name", "room_type", "price",
        "number_of_reviews", "last_review", "availability_365"]
print(df[near_dups].sort_values(key)[cols].head(20))

# Compare groups: same unit listed twice vs. different units in one building
compare = df[near_dups].groupby(key).agg(
    n_listings=("id", "count"),
    n_room_types=("room_type", "nunique"),
    n_prices=("price", "nunique"),
    total_reviews=("number_of_reviews", "sum"),
)
print(compare.sort_values("n_listings", ascending=False).head(15))

# ---------------------------------------------------------------
# Handle missing data
# ---------------------------------------------------------------
missing_before = df.isna().sum()
print(missing_before[missing_before > 0])

# Is the missing data structural (explained by other columns)?
print((df["reviews_per_month"].isna() == df["last_review"].isna()).all())
print((df.loc[df["reviews_per_month"].isna(), "number_of_reviews"] == 0).all())
print((df["host_id"].isna() == df["calculated_host_listings_count"].isna()).all())
print(df.loc[df["minimum_nights"].isna(), "availability_365"].describe())

# Flags first, while the original missing values are still visible
df["has_price"] = df["price"].notna()
df["never_reviewed"] = df["last_review"].isna()
df["host_missing"] = df["host_id"].isna()
df["license_listed"] = df["license"].notna()

# The only fill: no reviews means 0 reviews per month
df["reviews_per_month"] = df["reviews_per_month"].fillna(0)

# Missing counts before and after
missing_after = df.isna().sum().reindex(missing_before.index)

report = pd.DataFrame({"before": missing_before, "after": missing_after})
report = report[report["before"] > 0].copy()
report["pct_of_rows"] = (report["before"] / len(df) * 100).round(1)

report["action"] = pd.Series({
    "price": "kept missing, flagged (has_price)",
    "last_review": "kept missing, flagged (never_reviewed)",
    "reviews_per_month": "filled with 0",
    "host_id": "kept missing, flagged (host_missing)",
    "host_profile_id": "kept missing",
    "host_name": "kept missing",
    "calculated_host_listings_count": "kept missing",
    "minimum_nights": "kept missing",
    "license": "kept missing, flagged (license_listed)",
})
print(report)

# ---------------------------------------------------------------
# Check suspicious values
# ---------------------------------------------------------------
snapshot = df["last_review"].max()  # proxy for the scrape date
print("Earliest / latest review:", df["last_review"].min(), snapshot)

print("Future dates:", (df["last_review"] > pd.Timestamp.today()).sum())
print("Before Airbnb existed (2008):", (df["last_review"] < "2008-08-01").sum())

# Impossible values (every count should be 0)
impossible = {
    "price <= 0":                         (df["price"] <= 0).sum(),
    "minimum_nights < 1":                 (df["minimum_nights"] < 1).sum(),
    "availability outside 0-365":         ((df["availability_365"] < 0) | (df["availability_365"] > 365)).sum(),
    "negative review counts":             ((df["number_of_reviews"] < 0) | (df["number_of_reviews_ltm"] < 0)).sum(),
    "reviews_ltm > total reviews":        (df["number_of_reviews_ltm"] > df["number_of_reviews"]).sum(),
    "reviews > 0 but no last_review":     ((df["number_of_reviews"] > 0) & df["last_review"].isna()).sum(),
    "reviews == 0 but has last_review":   ((df["number_of_reviews"] == 0) & df["last_review"].notna()).sum(),
    "ltm > 0 but last review > 1 yr old": ((df["number_of_reviews_ltm"] > 0) &
                                           (df["last_review"] < snapshot - pd.Timedelta(days=366))).sum(),
    "coordinates outside LA County":      (~df["latitude"].between(33.2, 34.9) |
                                           ~df["longitude"].between(-119.0, -117.5)).sum(),
}
print(pd.Series(impossible))

# Unusual (but possibly valid) records: flag, don't delete
cols = ["id", "neighbourhood", "room_type", "price", "minimum_nights",
        "number_of_reviews", "reviews_per_month", "availability_365"]

# Price extremes within each room type
p01 = df.groupby("room_type")["price"].transform(lambda s: s.quantile(0.01))
p99 = df.groupby("room_type")["price"].transform(lambda s: s.quantile(0.99))
df["flag_price_high"] = df["price"] > p99
df["flag_price_low"] = df["price"] < p01

# Stays that make short-term booking impossible
df["flag_min_nights_gt_365"] = df["minimum_nights"] > 365

# Extreme review activity
df["flag_reviews_extreme"] = df["reviews_per_month"] > df["reviews_per_month"].quantile(0.999)

# Host portfolio size vs. what the file actually shows
actual_count = df.groupby("host_id")["id"].transform("count")
df["flag_host_count_mismatch"] = (
    (actual_count != df["calculated_host_listings_count"]) & df["host_id"].notna()
)

# Look at the extreme records yourself
print(df.nlargest(15, "price")[cols])
print(df.nsmallest(15, "price")[cols])
print(df.nlargest(10, "minimum_nights")[cols])
print(df.nlargest(10, "number_of_reviews")[cols])

# Licenses reused across many listings
print(df["license"].value_counts().head(10))

# Summary of all flags
flag_cols = [c for c in df.columns if c.startswith("flag_")]
print(df[flag_cols].sum())
print("Rows with at least one flag:", df[flag_cols].any(axis=1).sum())

# ---------------------------------------------------------------
# Reconcile changes (row counts and totals before vs. after)
# ---------------------------------------------------------------
start_rows = len(raw)
final_rows = len(df)
print("Starting rows:", start_rows)
print("Final rows:   ", final_rows)
print("Difference:   ", start_rows - final_rows)
print("Columns before/after:", raw.shape[1], "/", df.shape[1])  # flags add columns, not rows

# Which listings, if any, are missing from the cleaned data?
raw_ids = set(raw["id"].astype(str))
df_ids = set(df["id"].astype(str))
removed = raw_ids - df_ids
added = df_ids - raw_ids
print("IDs removed:", len(removed))
print("IDs added:  ", len(added))

# The accounting has to balance
assert start_rows - len(removed) + len(added) == final_rows, "Row counts don't reconcile"


def totals(d):
    return pd.Series({
        "rows": len(d),
        "distinct listing ids": d["id"].nunique(),
        "distinct hosts": d["host_id"].nunique(),
        "listings with a price": d["price"].notna().sum(),
        "median price": d["price"].median(),
        "mean price": d["price"].mean(),
        "total reviews": d["number_of_reviews"].sum(),
        "total reviews, last 12 months": d["number_of_reviews_ltm"].sum(),
        "mean reviews_per_month": d["reviews_per_month"].mean(),
        "share with min nights >= 30": (d["minimum_nights"].dropna() >= 30).mean(),
        "listings with a license": d["license"].notna().sum(),
        "distinct license values": d["license"].nunique(),
        "distinct listing names": d["name"].nunique(),
    })


comparison = pd.DataFrame({"raw": totals(raw), "cleaned": totals(df)})
comparison["change"] = comparison["cleaned"] - comparison["raw"]
print(comparison.round(2))

# ---------------------------------------------------------------
# Check calculations (records used per metric, missing group keys)
# ---------------------------------------------------------------
metrics = {
    "Total listings":                     (len(df), 0),
    "Median/mean price":                  (df["price"].notna().sum(), df["price"].isna().sum()),
    "Mean reviews/month (all listings)":  (len(df), 0),
    "Mean reviews/month (reviewed only)": ((~df["never_reviewed"]).sum(), df["never_reviewed"].sum()),
    "Share min nights >= 30":             (df["minimum_nights"].notna().sum(), df["minimum_nights"].isna().sum()),
    "Share from multi-listing hosts":     (df["calculated_host_listings_count"].notna().sum(),
                                           df["calculated_host_listings_count"].isna().sum()),
    "Share with a license":               (len(df), 0),
}
report = pd.DataFrame(metrics, index=["records_used", "records_excluded"]).T
print(report)

# Compute the shares with the right denominators
print((df["minimum_nights"].dropna() >= 30).mean())
print((df["calculated_host_listings_count"].dropna() > 1).mean())
print(df["license"].notna().mean())

# Missing group keys
print(df[["neighbourhood_group", "neighbourhood", "room_type", "host_id"]].isna().sum())

# Records behind each group average
print(df.groupby("room_type", dropna=False)["price"].agg(
    listings="size",       # all rows in the group
    priced="count",        # rows with a non-missing price
    median_price="median",
))

# ---------------------------------------------------------------
# Verify individual records
# ---------------------------------------------------------------


def show(v):
    return "<missing>" if pd.isna(v) else repr(v)


def same(a, b):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return a == b


# Pick records C, D, and E by condition (first matching row in the original)
idx_zero = raw.index[raw["license"].str.fullmatch(r"0\d+", na=False)][0]
idx_unrev = raw.index[raw["number_of_reviews"] == 0][0]
idx_nohost = raw.index[raw["host_id"].isna()][0]

# (label, index, column in df, EXPECTED value, column in raw to show as original)
checks = [
    ("A hidden chars + accent",  10883,      "host_name",         "Ray Pérez",                  "host_name"),
    ("B license capitalization", 2320,       "license",           "HSR19-005325",               "license"),
    ("C leading zero",           idx_zero,   "license",           raw.loc[idx_zero, "license"], "license"),
    ("D never reviewed",         idx_unrev,  "reviews_per_month", 0,                            "reviews_per_month"),
    ("D never reviewed",         idx_unrev,  "last_review",       pd.NaT,                       "last_review"),
    ("E unknown host",           idx_nohost, "host_id",           pd.NA,                        "host_id"),
    ("E unknown host",           idx_nohost, "host_missing",      True,                         "host_id"),
]

rows = []
for label, idx, col, expected, raw_col in checks:
    original = raw.loc[idx, raw_col]
    actual = df.loc[idx, col]
    rows.append({
        "record": label, "index": idx, "column": col,
        "original": show(original), "expected": show(expected),
        "actual": show(actual), "match": same(expected, actual),
    })

pd.set_option("display.max_colwidth", None)
print(pd.DataFrame(rows).to_string(index=False))
