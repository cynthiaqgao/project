from __future__ import annotations

import math

import pandas as pd


def is_missing(value) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def number(value, digits: int = 0) -> str:
    if is_missing(value):
        return "N/A"
    return f"{float(value):,.{digits}f}"


def usd(value, digits: int = 0) -> str:
    if is_missing(value):
        return "N/A"
    return f"${float(value):,.{digits}f}"


def pct(value, digits: int = 1) -> str:
    if is_missing(value):
        return "N/A"
    return f"{float(value) * 100:.{digits}f}%"


def metric_cards(columns, row, budget_row, room: str, budget: float | None) -> None:
    columns[0].metric("Matching listings", number(row.listing_count))
    columns[1].metric("Median listed nightly price", usd(row.median_price))
    columns[2].metric(
        "Within nightly budget",
        pct(budget_row.within_budget_share) if budget is not None else "Set a budget",
    )
    columns[3].metric("Reviewed listings", pct(row.reviewed_share))


def add_small_metric_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    checks = [
        ("price_n", "price_n<30"),
        ("review_n", "review_n<30"),
        ("review_ltm_n", "review_ltm_n<30"),
        ("availability_n", "availability_n<30"),
    ]
    result["small_sample_metrics"] = result.apply(
        lambda row: ", ".join(label for col, label in checks if row[col] < 30), axis=1
    )
    return result


def usable_max(series, fallback: float = 1.0) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return fallback
    maximum = float(values.max())
    return maximum if math.isfinite(maximum) and maximum > 0 else fallback
