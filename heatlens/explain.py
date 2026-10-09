"""Explainability engine for HeatLens: generates waterfall attribution and plain-language diagnostic sentences."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


INDICATOR_LABELS = {
    "c_lst": "Surface Temperature",
    "c_building": "Building Footprint Density",
    "c_veg_deficit": "Vegetation / Canopy Deficit",
    "c_pop_density": "High Population Density",
    "c_outdoor_proxy": "Outdoor Pedestrian & Worker Exposure",
    "c_elderly": "Elderly Resident Concentration",
    "c_child": "Young Children Concentration",
    "c_dist_cooling": "Cooling Shelter Distance Gap",
    "c_dist_water": "Drinking Water Distance Gap"
}


def get_cell_contributions_vs_median(row: pd.Series, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calculates each indicator's contribution relative to the study area median."""
    cols = list(INDICATOR_LABELS.keys())
    medians = df[cols].median()

    breakdown = []
    for col in cols:
        val = float(row[col])
        med = float(medians[col])
        delta = round(val - med, 2)
        breakdown.append({
            "indicator_key": col,
            "label": INDICATOR_LABELS[col],
            "contribution_points": val,
            "area_median_points": med,
            "excess_vs_median": delta
        })

    # Sort by excess descending
    breakdown.sort(key=lambda x: x["excess_vs_median"], reverse=True)
    return breakdown


def generate_explanation_sentence(row: pd.Series, df: pd.DataFrame) -> str:
    """Generates a dynamic, fully computed plain-language sentence explaining the cell's score drivers."""
    cell_id = row.get("cell_id", "Cell")
    score = round(float(row["risk_score"]), 1)
    tier = row.get("risk_tier", "Moderate")

    # Medians
    med_lst = float(df["lst_mean_c"].median())
    med_bldg = float(df["building_coverage"].median()) * 100.0
    med_cool = float(df["dist_cooling_m"].median()) / 1000.0

    # Cell values
    cell_lst = float(row["lst_mean_c"])
    cell_bldg = float(row["building_coverage"]) * 100.0
    cell_cool_km = float(row["dist_cooling_m"]) / 1000.0

    contributions = get_cell_contributions_vs_median(row, df)
    top_pos = [c for c in contributions if c["excess_vs_median"] > 0]
    top_neg = [c for c in contributions if c["excess_vs_median"] < 0]

    drivers_str = []
    if cell_lst > med_lst:
        delta_t = round(cell_lst - med_lst, 1)
        pts = round(row["c_lst"] - df["c_lst"].median(), 1)
        drivers_str.append(f"surface {delta_t}°C hotter than area median (+{pts} pts)")

    if cell_bldg > med_bldg:
        pts = round(row["c_building"] - df["c_building"].median(), 1)
        drivers_str.append(f"{round(cell_bldg, 0):.0f}% built-up coverage (+{pts} pts)")

    if cell_cool_km > med_cool:
        pts = round(row["c_dist_cooling"] - df["c_dist_cooling"].median(), 1)
        drivers_str.append(f"{cell_cool_km:.1f} km walk to nearest cooling centre (+{pts} pts)")

    if not drivers_str and top_pos:
        # Fallback to top excess indicators
        for t in top_pos[:2]:
            drivers_str.append(f"{t['label']} (+{t['excess_vs_median']} pts)")

    drivers_clause = ", ".join(drivers_str) if drivers_str else "distributed across multiple moderate factors"

    protective = []
    for neg in top_neg[-2:]:
        if neg["excess_vs_median"] < -2.0:
            protective.append(f"{neg['label']} ({neg['excess_vs_median']} pts)")
    protective_str = ", ".join(protective) if protective else "none"

    return f"Cell {cell_id} scores {score} ({tier}). Biggest drivers: {drivers_clause}. Protective: {protective_str}."
