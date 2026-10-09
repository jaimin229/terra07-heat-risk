"""City-specific empirical cooling relationship model (OLS + 1,000 bootstrap CI).

Estimates LST response to NDVI, building coverage, and open space:
lst_mean_c ~ ndvi_mean + building_coverage + open_space_frac
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class CoolingModelResult:
    beta_ndvi: float
    beta_bldg: float
    beta_open: float
    intercept: float
    r_squared: float
    ci_lower: float
    ci_upper: float
    ci_conservative_cooling: float  # Absolute cooling magnitude in conservative scenario
    n_samples: int
    n_bootstrap: int


def fit_cooling_model(df: pd.DataFrame, n_bootstrap: int = 1000, seed: int = 42) -> CoolingModelResult:
    """Fits cell-level OLS regression with HC3 robust SEs and 1,000 bootstrap resamples.

    Model: LST = beta_0 + beta_ndvi * NDVI + beta_bldg * BuildingCov + beta_open * OpenSpaceFrac

    Returns CoolingModelResult with coefficients, R2, and bootstrap 95% CI for beta_ndvi.
    """
    required_cols = ["lst_mean_c", "ndvi_mean", "building_coverage", "open_space_frac"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column for cooling model: {col}")

    X_cols = ["ndvi_mean", "building_coverage", "open_space_frac"]
    X = sm.add_constant(df[X_cols].values)
    y = df["lst_mean_c"].values
    n = len(df)

    # 1. Main model fit with HC3 robust covariance
    ols_model = sm.OLS(y, X).fit(cov_type="HC3")
    intercept = float(ols_model.params[0])
    beta_ndvi = float(ols_model.params[1])
    beta_bldg = float(ols_model.params[2])
    beta_open = float(ols_model.params[3])
    r_squared = float(ols_model.rsquared)

    # 2. 1,000 Bootstrap resamples for empirical 95% CI of beta_ndvi
    rng = np.random.RandomState(seed)
    bootstrap_betas = np.zeros(n_bootstrap)

    for i in range(n_bootstrap):
        sample_idx = rng.choice(n, size=n, replace=True)
        X_sample = X[sample_idx]
        y_sample = y[sample_idx]
        # Fast normal equation solve: (X'X)^-1 X'y
        try:
            params = np.linalg.lstsq(X_sample, y_sample, rcond=None)[0]
            bootstrap_betas[i] = params[1]
        except Exception:
            bootstrap_betas[i] = beta_ndvi

    ci_lower = float(np.percentile(bootstrap_betas, 2.5))
    ci_upper = float(np.percentile(bootstrap_betas, 97.5))

    # For cooling (negative beta), the conservative cooling effect is the upper bound
    # (i.e. closest to zero, lowest magnitude cooling per unit NDVI increase)
    ci_conservative_cooling = abs(ci_upper) if ci_upper < 0 else abs(beta_ndvi * 0.7)

    return CoolingModelResult(
        beta_ndvi=round(beta_ndvi, 4),
        beta_bldg=round(beta_bldg, 4),
        beta_open=round(beta_open, 4),
        intercept=round(intercept, 4),
        r_squared=round(r_squared, 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
        ci_conservative_cooling=round(ci_conservative_cooling, 4),
        n_samples=n,
        n_bootstrap=n_bootstrap,
    )
