"""Unified action ranking, benefit-cost optimization, and sequential budget knapsack allocator."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from heatlens.config import load_config, PROJECT_ROOT
from heatlens.actions.shade import evaluate_shade_interventions
from heatlens.actions.water import evaluate_water_points
from heatlens.actions.cooling_centres import evaluate_cooling_centres

ACTIONS_CSV = PROJECT_ROOT / "data" / "processed" / "actions.csv"


def build_unified_action_plan(
    df: pd.DataFrame,
    config=None,
    top_shade_k: int = 50,
    vulnerable_weighted: bool = False,
) -> pd.DataFrame:
    """Builds unified multi-intervention catalog ranked globally by benefit-cost ratio.

    Combines:
    - Canopy and Shade Sails (shade)
    - Drinking Water and Misting Kiosks (water_point)
    - Emergency Cooling Sanctuaries (cooling_centre)
    """
    if config is None:
        config = load_config()

    # 1. Evaluate individual intervention families
    shade_df = evaluate_shade_interventions(df, config=config, vulnerable_weighted=vulnerable_weighted)
    if not shade_df.empty and top_shade_k:
        shade_df = shade_df.head(top_shade_k)

    water_df = evaluate_water_points(df, config=config, vulnerable_weighted=vulnerable_weighted)
    cooling_df = evaluate_cooling_centres(df, config=config, vulnerable_weighted=vulnerable_weighted)

    unified_records = []

    # Map shade records
    if not shade_df.empty:
        for _, row in shade_df.iterrows():
            unified_records.append({
                "action_type": "shade",
                "rank_within_type": int(row["rank_within_type"]),
                "target_id": str(row["target_id"]),
                "cluster_name": str(row["cluster_name"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "people_benefited": int(row["people_benefited"]),
                "elderly_benefited": int(row["elderly_benefited"]),
                "impact": float(row["impact"]),
                "cost_inr": float(row["cost_inr"]),
                "benefit_cost": float(row["benefit_cost"]),
                "rationale": str(row["rationale"]),
                "evidence_drivers": f"Cooling: {row['delta_lst_central_c']}°C (CI: {row['ci_range_str']}), Risk drop: -{row['delta_risk']} pts",
            })

    # Map water records
    if not water_df.empty:
        for _, row in water_df.iterrows():
            unified_records.append({
                "action_type": "water_point",
                "rank_within_type": int(row["rank_within_type"]),
                "target_id": str(row["target_id"]),
                "cluster_name": str(row["cluster_name"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "people_benefited": int(row["people_benefited"]),
                "elderly_benefited": int(row["elderly_benefited"]),
                "impact": float(row["impact"]),
                "cost_inr": float(row["cost_inr"]),
                "benefit_cost": float(row["benefit_cost"]),
                "rationale": str(row["rationale"]),
                "evidence_drivers": f"Covers {row['cells_covered_count']} cells within 300m walking radius",
            })

    # Map cooling centre records
    if not cooling_df.empty:
        for _, row in cooling_df.iterrows():
            unified_records.append({
                "action_type": "cooling_centre",
                "rank_within_type": int(row["rank_within_type"]),
                "target_id": str(row["target_id"]),
                "cluster_name": str(row["cluster_name"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "people_benefited": int(row["people_benefited"]),
                "elderly_benefited": int(row["elderly_benefited"]),
                "impact": float(row["impact"]),
                "cost_inr": float(row["cost_inr"]),
                "benefit_cost": float(row["benefit_cost"]),
                "rationale": str(row["rationale"]),
                "evidence_drivers": f"Facility: {row['facility_name']} ({row['facility_type']}) covering 1,000m walk zone",
            })

    unified_df = pd.DataFrame(unified_records)
    if unified_df.empty:
        return unified_df

    # Global sort by benefit_cost descending
    unified_df = unified_df.sort_values("benefit_cost", ascending=False).reset_index(drop=True)
    unified_df["global_rank"] = range(1, len(unified_df) + 1)

    # Compute cumulative metrics
    unified_df["cumulative_cost_inr"] = unified_df["cost_inr"].cumsum()
    unified_df["cumulative_impact"] = unified_df["impact"].cumsum().round(2)
    unified_df["cumulative_people"] = unified_df["people_benefited"].cumsum()

    return unified_df


def optimize_budget_allocation(
    actions_df: pd.DataFrame,
    budget_inr: float = 10_000_000.0,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Selects highest-ROI action package feasible within given financial budget.

    Returns the selected subset of actions and aggregate portfolio KPIs.
    """
    if actions_df.empty:
        return pd.DataFrame(), {}

    selected = []
    spent = 0.0
    total_impact = 0.0
    total_people = 0.0
    total_elderly = 0.0

    for _, row in actions_df.iterrows():
        c = float(row["cost_inr"])
        if spent + c <= budget_inr:
            selected.append(row)
            spent += c
            total_impact += float(row["impact"])
            total_people += int(row["people_benefited"])
            total_elderly += int(row["elderly_benefited"])

    sel_df = pd.DataFrame(selected)
    summary = {
        "budget_total_inr": float(budget_inr),
        "budget_spent_inr": float(spent),
        "budget_remaining_inr": float(budget_inr - spent),
        "actions_selected_count": len(selected),
        "total_impact_points": round(total_impact, 2),
        "total_people_benefited": int(total_people),
        "total_elderly_benefited": int(total_elderly),
        "portfolio_benefit_cost": round((total_impact / max(spent, 1.0)) * 1e6, 2),
    }
    return sel_df, summary


def save_actions_csv(df: pd.DataFrame, output_path: Path = ACTIONS_CSV) -> Path:
    """Saves actions table to data/processed/actions.csv."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
