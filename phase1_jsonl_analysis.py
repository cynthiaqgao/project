"""Explore a manageable pandas sample of the Amazon Fashion JSONL reviews."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "Amazon_Fashion.jsonl"
SAMPLE_ROWS = 25_000


def load_sample() -> pd.DataFrame:
    """Read the first manageable review sample with pandas."""
    return pd.read_json(DATA_PATH, lines=True, nrows=SAMPLE_ROWS)


def explore_reviews(reviews: pd.DataFrame) -> dict[str, object]:
    """Return display-ready facts for the Phase 1 data-fit discussion."""
    reviews = reviews.copy()
    reviews["review_date"] = pd.to_datetime(reviews["timestamp"], unit="ms", errors="coerce")
    reviews["text_length"] = reviews["text"].str.len()
    rating_counts = reviews["rating"].value_counts().sort_index()
    product_counts = reviews.groupby("parent_asin").size().sort_values(ascending=False)
    return {
        "sample_rows": len(reviews),
        "sample_columns": list(reviews.columns),
        "date_min": reviews["review_date"].min().date().isoformat(),
        "date_max": reviews["review_date"].max().date().isoformat(),
        "unique_products": int(reviews["parent_asin"].nunique()),
        "unique_reviewers": int(reviews["user_id"].nunique()),
        "verified_percentage": float(reviews["verified_purchase"].mean()),
        "average_rating": float(reviews["rating"].mean()),
        "rating_counts": {str(key): int(value) for key, value in rating_counts.items()},
        "missing_values": reviews.isna().sum().to_dict(),
        "top_products_by_review_count": {
            str(key): int(value) for key, value in product_counts.head(10).items()
        },
        "median_review_text_length": float(reviews["text_length"].median()),
    }


if __name__ == "__main__":
    summary = explore_reviews(load_sample())
    for key, value in summary.items():
        print(f"{key}: {value}")