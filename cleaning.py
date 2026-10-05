import pandas as pd


REQUIRED_COLUMNS = [
    "id",
    "neighbourhood",
    "room_type",
    "price",
    "minimum_nights",
    "availability_365",
    "latitude",
    "longitude",
    "reviews_per_month",
    "last_review",
]


def clean_listings(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Return one analysis-ready row per Airbnb listing."""

    missing_columns = set(REQUIRED_COLUMNS) - set(raw_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    df = raw_df.copy()

    # One row should represent one unique listing.
    df = df.drop_duplicates(subset="id")

    # A listing without price or minimum-stay information cannot support
    # the market-comparison dashboard.
    df = df.dropna(subset=["price", "minimum_nights"])

    # No review activity is represented as zero monthly reviews.
    df["reviews_per_month"] = df["reviews_per_month"].fillna(0)

    # Keep dates in a consistent, usable format.
    df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")

    # Remove impossible values while retaining legitimate high-price listings.
    df = df[
        (df["price"] > 0)
        & (df["minimum_nights"] > 0)
        & (df["availability_365"].between(0, 365))
    ].copy()

    return df


def filter_listings(
    clean_df: pd.DataFrame,
    neighbourhoods: list[str] | None = None,
    room_types: list[str] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    max_minimum_nights: int | None = None,
) -> pd.DataFrame:
    """Return listings matching optional dashboard filters."""

    if min_price is not None and min_price < 0:
        raise ValueError("min_price cannot be negative")
    if max_price is not None and max_price < 0:
        raise ValueError("max_price cannot be negative")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("min_price cannot exceed max_price")
    if max_minimum_nights is not None and max_minimum_nights < 1:
        raise ValueError("max_minimum_nights must be at least 1")

    filtered = clean_df.copy()
    if neighbourhoods:
        filtered = filtered[filtered["neighbourhood"].isin(neighbourhoods)]
    if room_types:
        filtered = filtered[filtered["room_type"].isin(room_types)]
    if min_price is not None:
        filtered = filtered[filtered["price"] >= min_price]
    if max_price is not None:
        filtered = filtered[filtered["price"] <= max_price]
    if max_minimum_nights is not None:
        filtered = filtered[
            filtered["minimum_nights"] <= max_minimum_nights
        ]

    return filtered.copy()


def overview_metrics(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Return one row of KPI values for the selected listing set."""

    return pd.DataFrame(
        {
            "listing_count": [clean_df["id"].nunique()],
            "median_price": [clean_df["price"].median()],
            "average_available_nights": [clean_df["availability_365"].mean()],
            "average_reviews_per_month": [
                clean_df["reviews_per_month"].mean()
            ],
        }
    )


def market_summary(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Return dashboard metrics for each neighborhood and room-type segment."""

    summary = (
        clean_df.groupby(["neighbourhood", "room_type"], as_index=False)
        .agg(
            listing_count=("id", "nunique"),
            median_price=("price", "median"),
            average_available_nights=("availability_365", "mean"),
            average_reviews_per_month=("reviews_per_month", "mean"),
        )
    )

    return summary


def rank_market_segments(
    summary_df: pd.DataFrame,
    sort_by: str = "listing_count",
    min_listings: int = 30,
    ascending: bool = False,
) -> pd.DataFrame:
    """Return comparable market segments ranked by one chosen metric."""

    rankable_metrics = {
        "listing_count",
        "median_price",
        "average_available_nights",
        "average_reviews_per_month",
    }
    if sort_by not in rankable_metrics:
        raise ValueError(
            f"sort_by must be one of: {sorted(rankable_metrics)}"
        )
    if min_listings < 1:
        raise ValueError("min_listings must be at least 1")

    ranked = summary_df.loc[
        summary_df["listing_count"] >= min_listings
    ].copy()
    ranked = ranked.sort_values(sort_by, ascending=ascending).reset_index(drop=True)
    ranked.insert(0, "rank", ranked.index + 1)

    return ranked


if __name__ == "__main__":
    raw_df = pd.read_csv("LA_listings.csv")
    clean_df = clean_listings(raw_df)
    summary_df = market_summary(clean_df)
    ranked_segments = rank_market_segments(summary_df)

    print("Raw rows:", len(raw_df))
    print("Clean rows:", len(clean_df))
    print(ranked_segments.head())
