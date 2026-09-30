"""Pandas analysis layer for the Dodgers static HTML dashboard."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
LOCAL_DATA_DIR = ROOT / "data"
FALLBACK_DATA_DIR = ROOT.parents[1] / "04-unpack" / "data"
DATA_DIR = LOCAL_DATA_DIR if LOCAL_DATA_DIR.exists() else FALLBACK_DATA_DIR
OUTPUT_DIR = ROOT / "outputs"
BATTING_PATH = DATA_DIR / "09-LAD_batting.csv"
PITCHING_PATH = DATA_DIR / "09-LAD_pitching.csv"

BATTING_ROLE_MAP = {
	"C": "Catcher", "1B": "Infield", "2B": "Infield", "3B": "Infield",
	"SS": "Infield", "IF": "Infield", "MI": "Infield", "CI": "Infield",
	"LF": "Outfield", "CF": "Outfield", "RF": "Outfield", "OF": "Outfield",
	"DH": "Flex / other", "UT": "Flex / other", "P": "Flex / other",
}
PITCHING_ROLE_MAP = {"SP": "Starting pitcher", "RP": "Relief pitcher", "CL": "Closer"}
ROLE_ORDER = ["Catcher", "Infield", "Outfield", "Flex / other", "Unclassified"]


def load_batting() -> pd.DataFrame:
	return pd.read_csv(BATTING_PATH)


def load_pitching() -> pd.DataFrame:
	return pd.read_csv(PITCHING_PATH)


def available_seasons() -> list[int]:
	return sorted(load_batting()["Year"].astype(int).unique().tolist())


def _batting_with_roles() -> pd.DataFrame:
	batting = load_batting().copy()
	batting["Batting_Role"] = batting["Position"].map(BATTING_ROLE_MAP).fillna("Unclassified")
	return batting


def batting_role_summary(season: int) -> pd.DataFrame:
	batting = _batting_with_roles()
	season_batting = batting.loc[batting["Year"].eq(season)].copy()
	if season_batting.empty:
		raise ValueError(f"No batting records found for {season}.")
	summary = (
		season_batting.groupby("Batting_Role", as_index=False)
		.agg(
			player_season_rows=("Name", "size"),
			total_at_bats=("At_Bats", "sum"),
			total_hits=("Hits", "sum"),
			total_home_runs=("Home_Runs", "sum"),
		)
		.assign(
			combined_batting_average=lambda frame: (
				frame["total_hits"] / frame["total_at_bats"]
			).where(frame["total_at_bats"].ne(0))
		)
	)
	summary["role_sort"] = summary["Batting_Role"].map(
		{role: index for index, role in enumerate(ROLE_ORDER)}
	).fillna(len(ROLE_ORDER))
	summary = summary.sort_values(["role_sort", "Batting_Role"]).drop(columns="role_sort")
	if int(summary["player_season_rows"].sum()) != len(season_batting):
		raise ValueError("Batting role counts do not reconcile to the selected season.")
	return summary


def headline_metrics(season: int) -> dict[str, str]:
	summary = batting_role_summary(season)
	total_at_bats = int(summary["total_at_bats"].sum())
	total_hits = int(summary["total_hits"].sum())
	combined_ba = total_hits / total_at_bats if total_at_bats else 0
	return {
		"Player-season rows": f'{int(summary["player_season_rows"].sum()):,}',
		"Total at-bats": f"{total_at_bats:,}",
		"Combined batting average": f"{combined_ba:.3f}",
	}


def pitching_position_audit(season: int) -> dict[str, object]:
	pitching = load_pitching().copy()
	season_pitching = pitching.loc[pitching["Year"].eq(season)].copy()
	if season_pitching.empty:
		raise ValueError(f"No pitching records found for {season}.")
	season_pitching["Pitching_Role"] = season_pitching["Position"].map(PITCHING_ROLE_MAP).fillna("Unclassified")
	total_rows = len(season_pitching)
	missing_rows = int(season_pitching["Position"].isna().sum())
	role_counts = (
		season_pitching.groupby("Pitching_Role", as_index=False)
		.agg(player_season_rows=("Name", "size"))
		.sort_values("Pitching_Role")
	)
	if int(role_counts["player_season_rows"].sum()) != total_rows:
		raise ValueError("Pitching role counts do not reconcile to the selected season.")
	return {
		"total_rows": total_rows,
		"missing_rows": missing_rows,
		"missing_percentage_display": f"{missing_rows / total_rows:.1%}",
		"role_counts": [
			{"role": row.Pitching_Role, "rows": int(row.player_season_rows)}
			for row in role_counts.itertuples(index=False)
		],
	}


def yearly_batting_trend() -> pd.DataFrame:
	batting = load_batting().copy()
	return (
		batting.groupby("Year", as_index=False)
		.agg(player_season_rows=("Name", "size"), total_at_bats=("At_Bats", "sum"), total_hits=("Hits", "sum"))
		.assign(combined_batting_average=lambda frame: frame["total_hits"] / frame["total_at_bats"])
		.sort_values("Year")
	)


def _save_role_chart(summary: pd.DataFrame, season: int) -> Path:
	OUTPUT_DIR.mkdir(exist_ok=True)
	chart_path = OUTPUT_DIR / f"role_comparison_{season}.png"
	chart_data = summary.loc[summary["total_at_bats"].gt(0)].copy()
	figure, axis = plt.subplots(figsize=(8.5, 5.2))
	bars = axis.bar(chart_data["Batting_Role"], chart_data["combined_batting_average"], color="#005a9c")
	axis.set_title(f"Dodgers combined batting average by role - {season}", weight="bold")
	axis.set_xlabel("Batting role")
	axis.set_ylabel("Combined batting average (total H / total AB)")
	axis.set_ylim(0, max(0.35, float(chart_data["combined_batting_average"].max()) + 0.06))
	axis.grid(axis="y", alpha=0.25)
	axis.set_axisbelow(True)
	axis.tick_params(axis="x", rotation=15)
	for bar, value in zip(bars, chart_data["combined_batting_average"], strict=True):
		axis.text(bar.get_x() + bar.get_width() / 2, value + 0.006, f"{value:.3f}", ha="center", fontsize=9)
	figure.tight_layout()
	figure.savefig(chart_path, dpi=160, bbox_inches="tight")
	plt.close(figure)
	return chart_path


def _save_yearly_chart(trend: pd.DataFrame) -> Path:
	OUTPUT_DIR.mkdir(exist_ok=True)
	chart_path = OUTPUT_DIR / "yearly_trend.png"
	figure, axis = plt.subplots(figsize=(9, 5.2))
	axis.plot(trend["Year"], trend["combined_batting_average"], color="#005a9c", linewidth=2.2)
	axis.set_title("Dodgers combined batting average by season", weight="bold")
	axis.set_xlabel("Season")
	axis.set_ylabel("Combined batting average (total H / total AB)")
	axis.grid(alpha=0.25)
	axis.set_axisbelow(True)
	figure.tight_layout()
	figure.savefig(chart_path, dpi=160, bbox_inches="tight")
	plt.close(figure)
	return chart_path


def dashboard_data() -> dict[str, object]:
	seasons = available_seasons()
	selected_season = seasons[-1]
	by_season: dict[str, object] = {}
	for season in seasons:
		summary = batting_role_summary(season)
		_save_role_chart(summary, season)
		by_season[str(season)] = {
			"metrics": headline_metrics(season),
			"role_rows": [
				{
					"role": row.Batting_Role,
					"player_season_rows": f"{int(row.player_season_rows):,}",
					"total_at_bats": f"{int(row.total_at_bats):,}",
					"total_hits": f"{int(row.total_hits):,}",
					"total_home_runs": f"{int(row.total_home_runs):,}",
					"combined_batting_average": f"{row.combined_batting_average:.3f}" if pd.notna(row.combined_batting_average) else "N/A",
				}
				for row in summary.itertuples(index=False)
			],
			"pitching_audit": pitching_position_audit(season),
			"role_chart": f"outputs/role_comparison_{season}.png",
		}
	_save_yearly_chart(yearly_batting_trend())
	return {
		"seasons": seasons,
		"selected_season": selected_season,
		"by_season": by_season,
		"yearly_chart": "outputs/yearly_trend.png",
	}
