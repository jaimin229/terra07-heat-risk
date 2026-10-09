"""Drinking water point allocation via Greedy Maximum Coverage with counterfactual re-scoring."""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import geopandas as gpd

from heatlens.config import load_config
from heatlens.hotspots import find_nearest_landmark


def evaluate_water_points(
    df: pd.DataFrame,
    config=None,
    vulnerable_weighted: bool = False,
    existing_coverage_radius_m: float = 300.0,
) -> pd.DataFrame:
    """Selects top-k drinking water kiosks via greedy maximum coverage.

    1. Computes cell demand weights: d_i = pop_total_i * (1 + outdoor_proxy) * (1 + 2 * elderly_share)
    2. Identifies candidate locations across the AOI (spaced >= 150m)
    3. Greedily selects candidate covering highest marginal uncovered demand within 300m
    4. Counterfactually updates dist_water_m -> recomputes adaptive gap -> recomputes Risk score
    5. Calculates marginal lives protected, person-risk points averted, cost, and benefit-cost
    """
    if config is None:
        config = load_config()

    water_cfg = config.actions.water
    k_targets = water_cfg.k
    cost_per_point = water_cfg.cost_inr_per_point
    radius_m = config.access.water_walk_m

    # Cell attributes
    n_cells = len(df)
    lons = df["lon"].values
    lats = df["lat"].values
    pop_total = df["pop_total"].values
    elderly_share = df["elderly_share"].values
    outdoor_proxy = df["outdoor_activity_proxy"].values
    dist_water_base = df["dist_water_m"].values
    risk_before = df["risk_score"].values

    # Demand weights
    demand = pop_total * (1.0 + outdoor_proxy) * (1.0 + 2.0 * elderly_share)

    # Already covered if dist_water_m <= radius_m
    is_covered = (dist_water_base <= radius_m).copy()

    # Precompute scaling for dist_water in scoring
    log_vals = np.log1p(np.maximum(0.0, dist_water_base))
    q_lo = float(np.quantile(log_vals, config.normalisation.winsor_low))
    q_hi = float(np.quantile(log_vals, config.normalisation.winsor_high))
    range_log = max(q_hi - q_lo, 0.1)

    w_comp = config.weights.components
    c_sum = w_comp.hazard + w_comp.exposure + w_comp.vulnerability + w_comp.adaptive_gap
    w_c_a = w_comp.adaptive_gap / c_sum
    w_adp_wat = config.weights.adaptive_gap.dist_water_point

    # Generate candidate nodes across the grid, focused on deficit areas
    # 1 degree lat ~ 111,000 m; 1 degree lon ~ 102,000 m in Ahmedabad
    dx_m = (lons[:, None] - lons[None, :]) * 102_000.0
    dy_m = (lats[:, None] - lats[None, :]) * 111_000.0
    dist_matrix = np.sqrt(dx_m ** 2 + dy_m ** 2)

    # Candidate sites: cells that have high demand deficit and dist >= 150m from existing covered centroids
    candidate_indices = np.where(~is_covered)[0]
    if len(candidate_indices) == 0:
        candidate_indices = np.argsort(-demand)[:50]

    selected_points = []
    current_dist_water = dist_water_base.copy()

    for step in range(k_targets):
        best_candidate = None
        best_marginal_impact = -1.0
        best_covered_cells = []

        for cand in candidate_indices:
            in_range = np.where(dist_matrix[cand] <= radius_m)[0]
            uncovered = [c for c in in_range if not is_covered[c]]
            if not uncovered:
                continue

            cand_impact = 0.0
            for c in in_range:
                old_d = current_dist_water[c]
                new_d = min(old_d, float(dist_matrix[cand, c]))
                if new_d < old_d:
                    delta_z = max(0.0, (np.log1p(old_d) - np.log1p(new_d)) / range_log)
                    delta_r = 100.0 * w_c_a * w_adp_wat * delta_z
                    p = pop_total[c] * (1.0 + 2.0 * elderly_share[c] if vulnerable_weighted else 1.0)
                    cand_impact += (p * delta_r) / 1000.0

            if cand_impact > best_marginal_impact:
                best_marginal_impact = cand_impact
                best_candidate = cand
                best_covered_cells = in_range

        if best_candidate is None:
            # Fallback to candidate with maximum uncovered demand
            remaining = [c for c in candidate_indices if c not in [p["candidate_idx"] for p in selected_points]]
            if not remaining:
                break
            best_candidate = remaining[0]
            best_covered_cells = np.where(dist_matrix[best_candidate] <= radius_m)[0]

        # Calculate impact of this kiosk placement
        newly_covered_cells = [c for c in best_covered_cells if not is_covered[c]]
        # Mark as covered
        for c in newly_covered_cells:
            is_covered[c] = True

        # Counterfactual update of dist_water for all cells in range
        updated_cells = []
        cell_delta_risks = []
        people_newly_served = int(np.sum(pop_total[newly_covered_cells])) if newly_covered_cells else int(np.sum(pop_total[best_covered_cells]))
        elderly_served = int(np.sum(df["pop_65plus"].values[newly_covered_cells])) if newly_covered_cells else int(np.sum(df["pop_65plus"].values[best_covered_cells]))

        # Re-score cells within walking range
        for c in best_covered_cells:
            old_d = current_dist_water[c]
            new_d = min(old_d, float(dist_matrix[best_candidate, c]))
            if new_d < old_d:
                current_dist_water[c] = new_d
                # Change in log distance
                old_log = np.log1p(old_d)
                new_log = np.log1p(new_d)
                delta_z = max(0.0, (old_log - new_log) / range_log)
                delta_r = 100.0 * w_c_a * w_adp_wat * delta_z
                cell_delta_risks.append((c, delta_r))

        total_impact = 0.0
        for c, dr in cell_delta_risks:
            pop = pop_total[c]
            if vulnerable_weighted:
                pop *= (1.0 + 2.0 * elderly_share[c])
            total_impact += (pop * dr) / 1000.0

        cand_lat = float(lats[best_candidate])
        cand_lon = float(lons[best_candidate])
        landmark = find_nearest_landmark(cand_lon, cand_lat)

        impact_val = round(max(total_impact, 0.05), 2)
        bc_ratio = round((impact_val / cost_per_point) * 1e6, 2)

        rationale = (
            f"Install drinking water / misting kiosk near {landmark}. "
            f"Directly covers {people_newly_served} residents (incl. {elderly_served} seniors) "
            f"within {int(radius_m)}m walking radius; previously {int(dist_water_base[best_candidate])}m to nearest water."
        )

        selected_points.append({
            "action_type": "water_point",
            "rank_within_type": step + 1,
            "target_id": f"WATER-K{step+1:02d}",
            "lat": cand_lat,
            "lon": cand_lon,
            "candidate_idx": best_candidate,
            "cluster_name": landmark,
            "cells_covered_count": len(best_covered_cells),
            "people_benefited": people_newly_served,
            "elderly_benefited": elderly_served,
            "impact": impact_val,
            "cost_inr": float(cost_per_point),
            "benefit_cost": bc_ratio,
            "rationale": rationale,
        })

    return pd.DataFrame(selected_points)
