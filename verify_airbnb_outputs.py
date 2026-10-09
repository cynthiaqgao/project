"""Independent checks for the Airbnb cleaning deliverables."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
EXPECTED_SOURCE_HASH = (
    "d3b34461d0dc409dbe9f99573e3343e342dbcefbb0767b4b62d60b3beb4aceb2"
)


def verify() -> None:
    summary = json.loads((OUTPUT_DIR / "cleaning_summary.json").read_text())
    cleaned = pd.read_csv(
        OUTPUT_DIR / "listings_cleaned.csv", dtype={"id": "string"}
    )
    sample = pd.read_csv(
        OUTPUT_DIR / "listings_cleaned_sample.csv", dtype={"id": "string"}
    )
    comparison = pd.read_csv(OUTPUT_DIR / "market_comparison.csv")
    checks = pd.read_csv(
        OUTPUT_DIR / "five_record_checks.csv", dtype={"listing_id": "string"}
    )

    assert summary["source"]["sha256"] == EXPECTED_SOURCE_HASH
    assert summary["rows"] == {
        "starting": 43932,
        "exact_duplicates_removed": 0,
        "final": 43932,
        "difference": 0,
        "duplicate_ids": 0,
    }
    assert len(cleaned) == 43932
    assert cleaned["id"].notna().all() and cleaned["id"].is_unique
    assert not cleaned.duplicated().any()
    assert cleaned["price_missing_flag"].eq(cleaned["price"].isna()).all()
    assert cleaned["availability_365"].between(0, 365).all()
    assert cleaned["number_of_reviews"].ge(0).all()
    assert cleaned["number_of_reviews_ltm"].ge(0).all()
    assert cleaned["number_of_reviews_ltm"].le(
        cleaned["number_of_reviews"]
    ).all()
    assert int(cleaned["reviews_per_month_imputed_flag"].sum()) == 11311
    assert cleaned.loc[
        cleaned["reviews_per_month_imputed_flag"], "reviews_per_month"
    ].eq(0).all()
    assert int(cleaned["last_review_after_snapshot_flag"].sum()) == 97
    assert int(cleaned["reviews_ltm_over_365_flag"].sum()) == 2

    assert len(sample) == 50
    sensitive_sample_columns = {
        "name",
        "host_id",
        "host_profile_id",
        "host_name",
        "latitude",
        "longitude",
        "license",
    }
    assert sensitive_sample_columns.isdisjoint(sample.columns)
    assert int(comparison["listing_rows"].sum()) == len(cleaned)
    assert len(checks) == 5 and checks["matches_expected"].all()

    print("PASS: source hash and 43,932-row reconciliation match")
    print("PASS: listing IDs are complete and unique")
    print("PASS: numeric, review, availability, and flag checks match")
    print("PASS: grouped market comparison reconciles to cleaned rows")
    print("PASS: safe sample has 50 rows and excludes sensitive columns")
    print("PASS: all five original-to-cleaned record checks match")


if __name__ == "__main__":
    verify()

