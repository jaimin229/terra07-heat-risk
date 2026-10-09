"""Shade and urban greening intervention evaluation with counterfactual re-scoring."""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import geopandas as gpd

from heatlens.config import load_config
from heatlens.actions.cooling_model import fit_cooling_model, CoolingModelResult


def evaluate_shade_interventions(
    df: pd.DataFrame,
    config=None,
    cooling_model: Optional[CoolingModelResult] = None,
    vulnerable_weighted: bool = False,
    min_cooling_floor_c: float = 0.10,
) -> pd.DataFrame:
    """Evaluates cell-by-cell shade and canopy planting interventions.

    Re-runs the exact scoring model under counterfactual conditions:
    1. Plantable fraction p_i = min(max_plantable_fraction, open_space_frac)
    2. Delta NDVI_i = delta_ndvi * p_i / max_plantable_fraction
    3. Delta LST_i = beta_ndvi * Delta NDVI_i (central and conservative CI)
    4. Recomputes Risk_after with frozen baseline normalisation bounds
    5. Calculates impact = pop_i * (Risk_before - Risk_after) / 1000
    6. Benefit-cost ratio = impact / cost_inr * 1e6
    """
    if config is None:
        config = load_config()

    shade_cfg = config.actions.shade
    max_plantable = shade_cfg.max_plantable_fraction
    delta_ndvi_target = shade_cfg.delta_ndvi
    cost_per_0p1 = shade_cfg.cost_inr_per_cell_per_0p1_ndvi

    if cooling_model is None:
        cooling_model = fit_cooling_model(df)

    # Baseline values
    lst_base = df["lst_mean_c"].values
    ndvi_base = df["ndvi_mean"].values
    open_space = df["open_space_frac"].values
    pop_total = df["pop_total"].values
    elderly_share = df["elderly_share"].values
    risk_before = df["risk_score"].values
    cell_ids = df["cell_id"].values
    lats = df["lat"].values
    lons = df["lon"].values

    # Weights
    w_comp = config.weights.components
    c_sum = w_comp.hazard + w_comp.exposure + w_comp.vulnerability + w_comp.adaptive_gap
    w_c_h = w_comp.hazard / c_sum
    w_haz_lst = config.weights.hazard.lst
    w_haz_veg = config.weights.hazard.veg_deficit

    # Normalization scale parameters from baseline
    q_lo_lst = float(df["lst_mean_c"].quantile(config.normalisation.winsor_low))
    q_hi_lst = float(df["lst_mean_c"].quantile(config.normalisation.winsor_high))
    range_lst = max(q_hi_lst - q_lo_lst, 1.0)

    veg_deficit_base = 1.0 - np.clip(ndvi_base, 0.0, 1.0)
    q_lo_veg = float(np.quantile(veg_deficit_base, config.normalisation.winsor_low))
    q_hi_veg = float(np.quantile(veg_deficit_base, config.normalisation.winsor_high))
    range_veg = max(q_hi_veg - q_lo_veg, 0.01)

    # 1. Plantable fraction and Delta NDVI
    plantable_frac = np.clip(np.minimum(max_plantable, open_space), 0.0, max_plantable)
    delta_ndvi = (delta_ndvi_target * (plantable_frac / max_plantable)).round(4)

    # 2. Temperature reduction
    # beta_ndvi is negative, so cooling magnitude = |beta_ndvi| * delta_ndvi
    cooling_central = (abs(cooling_model.beta_ndvi) * delta_ndvi).round(2)
    # Conservative cooling based on upper CI bound
    cooling_conservative = (cooling_model.ci_conservative_cooling * delta_ndvi).round(2)

    # 3. Counterfactual change in risk
    # Change in z_lst: Delta LST / range_lst
    # Change in z_veg: Delta NDVI / range_veg
    delta_z_lst = cooling_conservative / range_lst
    delta_z_veg = delta_ndvi / range_veg

    delta_c_lst = 100.0 * w_c_h * w_haz_lst * delta_z_lst
    delta_c_veg = 100.0 * w_c_h * w_haz_veg * delta_z_veg
    delta_risk = np.maximum(0.0, (delta_c_lst + delta_c_veg)).round(2)
    risk_after = np.clip(risk_before - delta_risk, 0.0, 100.0).round(2)

    # 4. Common impact metric: person-risk points averted
    if vulnerable_weighted:
        vuln_mult = 1.0 + 2.0 * elderly_share
        impact = ((pop_total * vuln_mult * delta_risk) / 1000.0).round(2)
    else:
        impact = ((pop_total * delta_risk) / 1000.0).round(2)

    # 5. Cost in INR
    cost_inr = (cost_per_0p1 * (delta_ndvi / 0.10)).round(0)

    # 6. Benefit-cost ratio (points per ₹ million)
    benefit_cost = np.where(cost_inr > 0, (impact / cost_inr) * 1e6, 0.0).round(2)

    # Build results table
    results = []
    for i in range(len(df)):
        if cooling_central[i] < min_cooling_floor_c or cost_inr[i] <= 0:
            continue

        cluster_name = df.iloc[i].get("cluster_name", f"Cell {cell_ids[i]}")
        ci_str = f"{round(abs(cooling_model.ci_upper) * delta_ndvi[i], 2)}–{round(abs(cooling_model.ci_lower) * delta_ndvi[i], 2)} °C"
        rationale = (
            f"Add {round(plantable_frac[i]*100, 1)}% canopy in {cluster_name}. "
            f"Expected surface cooling ≈ {cooling_central[i]} °C (95% CI {ci_str}), "
            f"reducing cell risk by {delta_risk[i]} pts for {int(pop_total[i])} residents."
        )

        results.append({
            "action_type": "shade",
            "target_id": str(cell_ids[i]),
            "lat": float(lats[i]),
            "lon": float(lons[i]),
            "cluster_name": cluster_name,
            "delta_ndvi": float(delta_ndvi[i]),
            "delta_lst_central_c": float(cooling_central[i]),
            "delta_lst_conservative_c": float(cooling_conservative[i]),
            "ci_range_str": ci_str,
            "risk_before": float(risk_before[i]),
            "risk_after": float(risk_after[i]),
            "delta_risk": float(delta_risk[i]),
            "people_benefited": int(pop_total[i]),
            "elderly_benefited": int(df.iloc[i].get("pop_65plus", 0)),
            "impact": float(impact[i]),
            "cost_inr": float(cost_inr[i]),
            "benefit_cost": float(benefit_cost[i]),
            "rationale": rationale,
        })

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        res_df = res_df.sort_values("benefit_cost", ascending=False).reset_index(drop=True)
        res_df["rank_within_type"] = range(1, len(res_df) + 1)
    return res_df
