"""Sensitivity and Monte Carlo robustness analysis for HeatLens (Team TERRA07)."""

from typing import Dict, Any, Tuple
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from heatlens.config import load_config


def run_monte_carlo_sensitivity(df: gpd.GeoDataFrame, n_draws: int = 1000, seed: int = 42) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
    """Runs 1,000 Dirichlet Monte-Carlo weight perturbations to assess ranking stability and robustness."""
    rng = np.random.RandomState(seed)
    n_cells = len(df)

    # Baseline component normalized scores (0 to 1)
    h = (df["comp_hazard"] / 35.0).clip(0.0, 1.0).values
    e = (df["comp_exposure"] / 25.0).clip(0.0, 1.0).values
    v = (df["comp_vulnerability"] / 25.0).clip(0.0, 1.0).values
    a = (df["comp_adaptive_gap"] / 15.0).clip(0.0, 1.0).values

    # Base ranks (1 = highest risk)
    base_ranks = (-df["risk_score"].values).argsort().argsort() + 1
    top_decile_cutoff = int(np.ceil(0.10 * n_cells))
    base_top_decile = base_ranks <= top_decile_cutoff

    # Dirichlet centered on (0.35, 0.25, 0.25, 0.15) with concentration 20
    alpha = np.array([0.35, 0.25, 0.25, 0.15]) * 20.0
    weight_samples = rng.dirichlet(alpha, size=n_draws)

    rank_matrix = np.zeros((n_draws, n_cells), dtype=int)
    spearman_corrs = []

    for draw_idx in range(n_draws):
        w_h, w_e, w_v, w_a = weight_samples[draw_idx]
        perturbed_risk = 100.0 * (w_h * h + w_e * e + w_v * v + w_a * a)
        perturbed_ranks = (-perturbed_risk).argsort().argsort() + 1
        rank_matrix[draw_idx] = perturbed_ranks
        r_sp, _ = spearmanr(base_ranks, perturbed_ranks)
        spearman_corrs.append(r_sp)

    # Per-cell metrics
    median_ranks = np.median(rank_matrix, axis=0)
    p05_ranks = np.percentile(rank_matrix, 5, axis=0)
    p95_ranks = np.percentile(rank_matrix, 95, axis=0)

    # Top-decile stability: fraction of draws cell is in top decile
    in_top_decile_counts = np.sum(rank_matrix <= top_decile_cutoff, axis=0)
    stability = in_top_decile_counts / float(n_draws)

    # Robust hotspot badge: stability >= 0.8
    is_robust_hotspot = stability >= 0.80

    # Geometric mean comparison
    # Geometric Risk = 100 * (H^0.35 * E^0.25 * V^0.25 * A^0.15)
    eps = 0.01
    geom_risk = 100.0 * ((h + eps) ** 0.35 * (e + eps) ** 0.25 * (v + eps) ** 0.25 * (a + eps) ** 0.15)
    r_geom, _ = spearmanr(df["risk_score"], geom_risk)

    # Assign to dataframe
    result_gdf = df.copy()
    result_gdf["median_rank"] = median_ranks.round(1)
    result_gdf["rank_ci_lower"] = p05_ranks.astype(int)
    result_gdf["rank_ci_upper"] = p95_ranks.astype(int)
    result_gdf["top_decile_stability"] = stability.round(3)
    result_gdf["is_robust_hotspot"] = is_robust_hotspot

    # Summary statistics
    robust_count = int(np.sum(is_robust_hotspot))
    base_top_decile_stable = np.sum((stability >= 0.80) & base_top_decile)
    pct_top_decile_stable = (base_top_decile_stable / float(np.sum(base_top_decile))) * 100.0

    summary = {
        "n_monte_carlo_draws": n_draws,
        "mean_spearman_rank_correlation": round(float(np.mean(spearman_corrs)), 4),
        "mean_spearman_perturbed": round(float(np.mean(spearman_corrs)), 4),
        "min_spearman_rank_correlation": round(float(np.min(spearman_corrs)), 4),
        "p05_spearman": round(float(np.percentile(spearman_corrs, 5)), 4),
        "geometric_vs_additive_spearman": round(float(r_geom), 4),
        "spearman_vs_geometric": round(float(r_geom), 4),
        "total_robust_hotspots": robust_count,
        "robust_hotspots_count": robust_count,
        "pct_baseline_top_decile_stable_in_80pct_draws": round(float(pct_top_decile_stable), 1),
    }

    return result_gdf, summary
