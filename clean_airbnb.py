"""Clean and validate the Los Angeles Inside Airbnb listings snapshot.

Input grain: one listing per row, keyed by ``id``.
Output grain: one listing per row, keyed by ``id``.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "listings.csv"
OUTPUT_DIR = ROOT / "outputs"
CLEAN_PATH = OUTPUT_DIR / "listings_cleaned.csv"
SAMPLE_PATH = OUTPUT_DIR / "listings_cleaned_sample.csv"
SUMMARY_PATH = OUTPUT_DIR / "cleaning_summary.json"
CHECKS_PATH = OUTPUT_DIR / "five_record_checks.csv"
COMPARISON_PATH = OUTPUT_DIR / "market_comparison.csv"

SNAPSHOT_LABEL = "Los Angeles listings snapshot supplied to the team"
SNAPSHOT_DATE = pd.Timestamp("2026-06-15")
SOURCE_URL = "https://insideairbnb.com/get-the-data/"

IDENTIFIER_COLUMNS = ["id", "host_id", "host_profile_id"]
TEXT_COLUMNS = [
    "name",
    "host_name",
    "neighbourhood_group",
    "neighbourhood",
    "room_type",
    "license",
]
INTEGER_COLUMNS = [
    "minimum_nights",
    "number_of_reviews",
    "calculated_host_listings_count",
    "availability_365",
    "number_of_reviews_ltm",
]
FLOAT_COLUMNS = ["latitude", "longitude", "price", "reviews_per_month"]
EXPECTED_COLUMNS = IDENTIFIER_COLUMNS + [
    "name",
    "host_name",
    "neighbourhood_group",
    "neighbourhood",
    "latitude",
    "longitude",
    "room_type",
    "price",
    "minimum_nights",
    "number_of_reviews",
    "last_review",
    "reviews_per_month",
    "calculated_host_listings_count",
    "availability_365",
    "number_of_reviews_ltm",
    "license",
]
SAMPLE_COLUMNS = [
    "id",
    "neighbourhood_group",
    "neighbourhood",
    "room_type",
    "price",
    "minimum_nights",
    "number_of_reviews",
    "last_review",
    "reviews_per_month",
    "calculated_host_listings_count",
    "availability_365",
    "number_of_reviews_ltm",
    "price_missing_flag",
    "price_outlier_flag",
    "minimum_nights_missing_flag",
    "minimum_nights_over_365_flag",
    "reviews_per_month_imputed_flag",
    "last_review_after_snapshot_flag",
    "reviews_ltm_over_365_flag",
    "host_identity_missing_flag",
    "license_reported",
    "sample_reason",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _remove_format_characters(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    return "".join(
        character
        for character in str(value)
        if unicodedata.category(character) != "Cf"
    )


def _normalize_text(series: pd.Series) -> pd.Series:
    cleaned = series.map(_remove_format_characters).astype("string")
    cleaned = cleaned.str.strip().str.replace(r"\s+", " ", regex=True)
    return cleaned.mask(cleaned.eq(""), pd.NA)


def _conversion_failure_count(original: pd.Series, converted: pd.Series) -> int:
    return int(original.notna().sum() - converted.notna().sum())


def load_source(path: Path = SOURCE_PATH) -> pd.DataFrame:
    """Load source values as strings so conversion evidence remains auditable."""
    source = pd.read_csv(path, dtype="string", keep_default_na=False)
    source = source.replace(r"^\s*$", pd.NA, regex=True)
    missing_columns = sorted(set(EXPECTED_COLUMNS) - set(source.columns))
    if missing_columns:
        raise ValueError(f"Source is missing columns: {missing_columns}")
    return source.loc[:, EXPECTED_COLUMNS].copy()


def clean_listings(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply documented cleaning rules and return cleaned rows plus evidence."""
    source_rows = len(raw)
    exact_duplicate_rows = int(raw.duplicated().sum())
    cleaned = raw.drop_duplicates().copy()

    text_before = cleaned[TEXT_COLUMNS].copy()
    for column in IDENTIFIER_COLUMNS:
        cleaned[column] = cleaned[column].astype("string").str.strip()
    for column in TEXT_COLUMNS:
        cleaned[column] = _normalize_text(cleaned[column])

    text_change_counts = {
        column: int(
            text_before[column]
            .fillna("<MISSING>")
            .ne(cleaned[column].fillna("<MISSING>"))
            .sum()
        )
        for column in TEXT_COLUMNS
    }

    conversion_failures: dict[str, int] = {}
    for column in INTEGER_COLUMNS:
        converted = pd.to_numeric(cleaned[column], errors="coerce")
        conversion_failures[column] = _conversion_failure_count(
            cleaned[column], converted
        )
        non_integer = converted.notna() & converted.mod(1).ne(0)
        if non_integer.any():
            raise ValueError(f"{column} contains non-integer numeric values.")
        cleaned[column] = converted.astype("Int64")

    for column in FLOAT_COLUMNS:
        converted = pd.to_numeric(cleaned[column], errors="coerce")
        conversion_failures[column] = _conversion_failure_count(
            cleaned[column], converted
        )
        cleaned[column] = converted.astype("Float64")

    parsed_dates = pd.to_datetime(cleaned["last_review"], errors="coerce")
    conversion_failures["last_review"] = _conversion_failure_count(
        cleaned["last_review"], parsed_dates
    )
    cleaned["last_review"] = parsed_dates

    missing_before = {
        column: int(cleaned[column].isna().sum()) for column in cleaned.columns
    }

    missing_review_rate = cleaned["reviews_per_month"].isna()
    zero_reviews = cleaned["number_of_reviews"].eq(0)
    review_rate_imputation = missing_review_rate & zero_reviews
    cleaned["reviews_per_month_imputed_flag"] = review_rate_imputation
    cleaned.loc[review_rate_imputation, "reviews_per_month"] = 0.0

    price_99th_percentile = float(cleaned["price"].quantile(0.99))
    cleaned["price_missing_flag"] = cleaned["price"].isna()
    cleaned["price_outlier_flag"] = cleaned["price"].gt(price_99th_percentile)
    cleaned["minimum_nights_missing_flag"] = cleaned["minimum_nights"].isna()
    cleaned["minimum_nights_over_365_flag"] = cleaned["minimum_nights"].gt(365)
    cleaned["last_review_after_snapshot_flag"] = cleaned["last_review"].gt(
        SNAPSHOT_DATE
    )
    cleaned["reviews_ltm_over_365_flag"] = cleaned["number_of_reviews_ltm"].gt(
        365
    )
    cleaned["host_identity_missing_flag"] = cleaned[
        ["host_id", "host_profile_id", "host_name"]
    ].isna().any(axis=1)
    cleaned["license_reported"] = cleaned["license"].notna()

    duplicate_ids = int(
        cleaned.loc[cleaned["id"].notna(), "id"].duplicated().sum()
    )
    if cleaned["id"].isna().any() or duplicate_ids:
        raise ValueError(
            "Listing id must be nonmissing and unique; investigate source records."
        )

    invalid_checks = {
        "nonpositive_price": cleaned["price"].notna() & cleaned["price"].le(0),
        "nonpositive_minimum_nights": cleaned["minimum_nights"].notna()
        & cleaned["minimum_nights"].le(0),
        "negative_total_reviews": cleaned["number_of_reviews"].lt(0),
        "negative_ltm_reviews": cleaned["number_of_reviews_ltm"].lt(0),
        "ltm_reviews_above_total": cleaned["number_of_reviews_ltm"].gt(
            cleaned["number_of_reviews"]
        ),
        "availability_outside_0_365": ~cleaned["availability_365"].between(
            0, 365
        ),
        "latitude_outside_global_range": ~cleaned["latitude"].between(-90, 90),
        "longitude_outside_global_range": ~cleaned["longitude"].between(
            -180, 180
        ),
        "zero_reviews_with_last_review": cleaned["number_of_reviews"].eq(0)
        & cleaned["last_review"].notna(),
        "positive_reviews_without_last_review": cleaned["number_of_reviews"].gt(0)
        & cleaned["last_review"].isna(),
        "positive_reviews_without_review_rate": cleaned["number_of_reviews"].gt(0)
        & cleaned["reviews_per_month"].isna(),
    }
    invalid_counts = {
        label: int(mask.fillna(False).sum())
        for label, mask in invalid_checks.items()
    }
    if any(invalid_counts.values()):
        raise ValueError(f"Validation failures found: {invalid_counts}")

    missing_after = {
        column: int(cleaned[column].isna().sum())
        for column in EXPECTED_COLUMNS
    }
    summary: dict[str, Any] = {
        "source": {
            "label": SNAPSHOT_LABEL,
            "official_snapshot_path_date": SNAPSHOT_DATE.date().isoformat(),
            "local_file_modified_date": pd.Timestamp(
                SOURCE_PATH.stat().st_mtime, unit="s"
            ).date().isoformat(),
            "url": SOURCE_URL,
            "file": SOURCE_PATH.name,
            "sha256": _sha256(SOURCE_PATH),
        },
        "grain": {
            "input": "one Airbnb listing per row",
            "output": "one Airbnb listing per row",
            "unique_key": "id",
        },
        "rows": {
            "starting": source_rows,
            "exact_duplicates_removed": exact_duplicate_rows,
            "final": len(cleaned),
            "difference": len(cleaned) - source_rows,
            "duplicate_ids": duplicate_ids,
        },
        "conversion_failures": conversion_failures,
        "text_values_changed": text_change_counts,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "rules_applied": {
            "review_rates_filled_with_zero": int(review_rate_imputation.sum()),
            "price_missing_flagged": int(cleaned["price_missing_flag"].sum()),
            "price_99th_percentile": price_99th_percentile,
            "price_outliers_flagged": int(cleaned["price_outlier_flag"].sum()),
            "minimum_nights_missing_flagged": int(
                cleaned["minimum_nights_missing_flag"].sum()
            ),
            "minimum_nights_over_365_flagged": int(
                cleaned["minimum_nights_over_365_flag"].sum()
            ),
            "last_review_after_snapshot_flagged": int(
                cleaned["last_review_after_snapshot_flag"].sum()
            ),
            "reviews_ltm_over_365_flagged": int(
                cleaned["reviews_ltm_over_365_flag"].sum()
            ),
            "host_identity_missing_flagged": int(
                cleaned["host_identity_missing_flag"].sum()
            ),
            "license_reported": int(cleaned["license_reported"].sum()),
            "license_missing": int(cleaned["license"].isna().sum()),
        },
        "invalid_value_checks": invalid_counts,
        "metric_denominators": {
            "price_nonmissing_rows": int(cleaned["price"].notna().sum()),
            "availability_rows": int(cleaned["availability_365"].notna().sum()),
            "review_activity_rows": int(cleaned["number_of_reviews_ltm"].notna().sum()),
        },
        "date_range": {
            "earliest_last_review": cleaned["last_review"].min().date().isoformat(),
            "latest_last_review": cleaned["last_review"].max().date().isoformat(),
        },
    }
    return cleaned, summary


def build_market_comparison(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return one neighbourhood-group/room-type combination per row."""
    comparison = (
        cleaned.groupby(
            ["neighbourhood_group", "room_type"],
            as_index=False,
            dropna=False,
        )
        .agg(
            listing_rows=("id", "size"),
            listings_with_price=("price", "count"),
            median_price=("price", "median"),
            median_availability_365=("availability_365", "median"),
            total_reviews_ltm=("number_of_reviews_ltm", "sum"),
            median_reviews_ltm=("number_of_reviews_ltm", "median"),
        )
        .sort_values(
            ["neighbourhood_group", "listing_rows", "room_type"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )
    if int(comparison["listing_rows"].sum()) != len(cleaned):
        raise ValueError("Grouped listing counts do not reconcile to cleaned rows.")
    return comparison


def build_safe_sample(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Select 50 deterministic rows, including difficult cleaning cases."""
    reasons = [
        ("missing price", cleaned["price_missing_flag"]),
        ("price above p99", cleaned["price_outlier_flag"]),
        ("minimum nights missing", cleaned["minimum_nights_missing_flag"]),
        ("minimum nights over 365", cleaned["minimum_nights_over_365_flag"]),
        ("review rate filled for zero reviews", cleaned["reviews_per_month_imputed_flag"]),
        ("review date after snapshot label", cleaned["last_review_after_snapshot_flag"]),
        ("more than 365 reviews in last year", cleaned["reviews_ltm_over_365_flag"]),
        ("host identity incomplete", cleaned["host_identity_missing_flag"]),
        ("license reported", cleaned["license_reported"]),
    ]
    selected: dict[str, str] = {}
    for reason, mask in reasons:
        for listing_id in cleaned.loc[mask.fillna(False), "id"].head(5):
            selected.setdefault(str(listing_id), reason)

    remaining_count = 50 - len(selected)
    if remaining_count > 0:
        remaining = cleaned.loc[~cleaned["id"].isin(selected)].sample(
            n=min(remaining_count, len(cleaned) - len(selected)),
            random_state=576,
        )
        for listing_id in remaining["id"]:
            selected[str(listing_id)] = "deterministic random context row"

    sample = cleaned.loc[cleaned["id"].isin(selected)].copy()
    sample["sample_reason"] = sample["id"].map(selected)
    return sample.loc[:, SAMPLE_COLUMNS].sort_values(
        ["sample_reason", "id"]
    ).reset_index(drop=True)


def build_record_checks(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    """Create five deterministic original-to-cleaned record checks."""
    raw_by_id = raw.set_index("id", drop=False)
    clean_by_id = cleaned.set_index("id", drop=False)
    checks: list[dict[str, object]] = []

    format_mask = raw["host_name"].fillna("").map(
        lambda value: any(unicodedata.category(ch) == "Cf" for ch in value)
    )
    format_id = str(raw.loc[format_mask, "id"].iloc[0])
    original_host = raw_by_id.at[format_id, "host_name"]
    cleaned_host = clean_by_id.at[format_id, "host_name"]
    checks.append(
        {
            "case": "invisible Unicode format characters",
            "listing_id": format_id,
            "reason": "remove invisible formatting but preserve the host label",
            "original_value": repr(original_host),
            "expected_value": repr(_normalize_text(pd.Series([original_host])).iloc[0]),
            "actual_value": repr(cleaned_host),
            "matches_expected": cleaned_host
            == _normalize_text(pd.Series([original_host])).iloc[0],
        }
    )

    missing_price_id = str(raw.loc[raw["price"].isna(), "id"].iloc[0])
    checks.append(
        {
            "case": "missing price retained",
            "listing_id": missing_price_id,
            "reason": "do not invent a nightly price",
            "original_value": "<missing>",
            "expected_value": "price missing; flag True",
            "actual_value": f"price missing; flag {bool(clean_by_id.at[missing_price_id, 'price_missing_flag'])}",
            "matches_expected": pd.isna(clean_by_id.at[missing_price_id, "price"])
            and bool(clean_by_id.at[missing_price_id, "price_missing_flag"]),
        }
    )

    zero_review_mask = raw["number_of_reviews"].eq("0") & raw[
        "reviews_per_month"
    ].isna()
    zero_review_id = str(raw.loc[zero_review_mask, "id"].iloc[0])
    checks.append(
        {
            "case": "structurally missing review rate",
            "listing_id": zero_review_id,
            "reason": "zero total reviews support a zero observed monthly review rate",
            "original_value": "reviews=0; reviews_per_month=<missing>",
            "expected_value": "reviews_per_month=0; imputed flag True",
            "actual_value": (
                f"reviews_per_month={float(clean_by_id.at[zero_review_id, 'reviews_per_month']):.1f}; "
                f"imputed flag {bool(clean_by_id.at[zero_review_id, 'reviews_per_month_imputed_flag'])}"
            ),
            "matches_expected": clean_by_id.at[zero_review_id, "reviews_per_month"]
            == 0
            and bool(
                clean_by_id.at[
                    zero_review_id, "reviews_per_month_imputed_flag"
                ]
            ),
        }
    )

    raw_minimum = pd.to_numeric(raw["minimum_nights"], errors="coerce")
    long_stay_id = str(raw.loc[raw_minimum.gt(365), "id"].iloc[0])
    long_stay_value = int(clean_by_id.at[long_stay_id, "minimum_nights"])
    checks.append(
        {
            "case": "unusually long minimum stay",
            "listing_id": long_stay_id,
            "reason": "retain a plausible policy value but flag it",
            "original_value": str(raw_by_id.at[long_stay_id, "minimum_nights"]),
            "expected_value": f"minimum_nights={long_stay_value}; over-365 flag True",
            "actual_value": (
                f"minimum_nights={long_stay_value}; over-365 flag "
                f"{bool(clean_by_id.at[long_stay_id, 'minimum_nights_over_365_flag'])}"
            ),
            "matches_expected": bool(
                clean_by_id.at[long_stay_id, "minimum_nights_over_365_flag"]
            ),
        }
    )

    after_snapshot_id = str(
        cleaned.loc[cleaned["last_review_after_snapshot_flag"], "id"].iloc[0]
    )
    after_snapshot_date = clean_by_id.at[after_snapshot_id, "last_review"].date().isoformat()
    checks.append(
        {
            "case": "review date after snapshot label",
            "listing_id": after_snapshot_id,
            "reason": "retain source value but flag the timing discrepancy",
            "original_value": str(raw_by_id.at[after_snapshot_id, "last_review"]),
            "expected_value": f"last_review={after_snapshot_date}; after-snapshot flag True",
            "actual_value": (
                f"last_review={after_snapshot_date}; after-snapshot flag "
                f"{bool(clean_by_id.at[after_snapshot_id, 'last_review_after_snapshot_flag'])}"
            ),
            "matches_expected": bool(
                clean_by_id.at[after_snapshot_id, "last_review_after_snapshot_flag"]
            ),
        }
    )

    return pd.DataFrame(checks)


def run_cleaning() -> dict[str, Any]:
    """Run the full workflow and write reproducible deliverables."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    raw = load_source()
    cleaned, summary = clean_listings(raw)
    comparison = build_market_comparison(cleaned)
    sample = build_safe_sample(cleaned)
    checks = build_record_checks(raw, cleaned)

    cleaned.to_csv(CLEAN_PATH, index=False, date_format="%Y-%m-%d")
    sample.to_csv(SAMPLE_PATH, index=False, date_format="%Y-%m-%d")
    comparison.to_csv(COMPARISON_PATH, index=False)
    checks.to_csv(CHECKS_PATH, index=False)

    summary["outputs"] = {
        "cleaned_file": CLEAN_PATH.name,
        "cleaned_rows": len(cleaned),
        "sample_file": SAMPLE_PATH.name,
        "sample_rows": len(sample),
        "comparison_file": COMPARISON_PATH.name,
        "comparison_rows": len(comparison),
        "record_checks_file": CHECKS_PATH.name,
        "record_checks_passed": int(checks["matches_expected"].sum()),
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    result = run_cleaning()
    print(json.dumps(result, indent=2, sort_keys=True))
