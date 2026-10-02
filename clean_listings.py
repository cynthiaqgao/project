from pathlib import Path
import pandas as pd


# Find the original CSV beside this script.
project_folder = Path(__file__).resolve().parent
data_path = project_folder / "LA_listings.csv"

if not data_path.exists():
    raise FileNotFoundError(f"Could not find: {data_path}")

# Read the original data without changing the source file.
raw = pd.read_csv(
    data_path,
    dtype={
        "id": "string",
        "host_id": "string",
        "host_profile_id": "string",
    },
)

# Apply the documented cleaning rules to a copy.
clean = raw.copy()
clean["name"] = clean["name"].astype("string").str.strip()
clean["last_review"] = pd.to_datetime(
    clean["last_review"], errors="coerce"
)
clean["minimum_nights"] = clean["minimum_nights"].astype("Int64")
clean["calculated_host_listings_count"] = (
    clean["calculated_host_listings_count"].astype("Int64")
)

# Check the cleaned data.
date_failures = raw["last_review"].notna() & clean["last_review"].isna()
name_has_outer_whitespace = (
    clean["name"].notna()
    & clean["name"].ne(clean["name"].str.strip())
)

assert len(raw) == len(clean), "The row count changed."
assert clean["id"].duplicated().sum() == 0, "Repeated listing IDs found."
assert int(date_failures.sum()) == 0, "Date conversion failures found."
assert int(name_has_outer_whitespace.sum()) == 0, "Untrimmed names found."

# Select up to 50 rows, including examples of important cleaning cases.
selected_indices = []
cases = [
    raw["name"].astype("string").ne(clean["name"]).fillna(False),
    clean["price"].isna(),
    clean["minimum_nights"].isna(),
    clean["number_of_reviews"].eq(0),
    clean["license"].isna(),
    clean["host_id"].isna(),
]

for mask in cases:
    for index in clean.index[mask]:
        if index not in selected_indices:
            selected_indices.append(index)
            break

# Include each room type and neighborhood group when available.
for column in ["room_type", "neighbourhood_group"]:
    for value in clean[column].dropna().unique():
        for index in clean.index[clean[column].eq(value)]:
            if index not in selected_indices:
                selected_indices.append(index)
                break

# Fill the sample to 50 rows using a fixed seed.
remaining_indices = clean.index.difference(selected_indices)
needed = min(50 - len(selected_indices), len(remaining_indices))

if needed > 0:
    selected_indices.extend(
        clean.loc[remaining_indices]
        .sample(n=needed, random_state=576)
        .index.tolist()
    )

cleaned_sample = clean.loc[selected_indices].copy()
sample_path = project_folder / "cleaned_sample.csv"
cleaned_sample.to_csv(sample_path, index=False)

print("Raw shape:", raw.shape)
print("Clean shape:", clean.shape)
print("Date conversion failures:", int(date_failures.sum()))
print("Sample rows:", len(cleaned_sample))
print("Sample saved to:", sample_path)