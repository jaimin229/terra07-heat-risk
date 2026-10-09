"""Action ranking and counterfactual evaluation modules for HeatLens."""

from heatlens.actions.cooling_model import fit_cooling_model, CoolingModelResult
from heatlens.actions.shade import evaluate_shade_interventions
from heatlens.actions.water import evaluate_water_points
from heatlens.actions.cooling_centres import evaluate_cooling_centres
from heatlens.actions.rank import build_unified_action_plan, save_actions_csv

__all__ = [
    "fit_cooling_model",
    "CoolingModelResult",
    "evaluate_shade_interventions",
    "evaluate_water_points",
    "evaluate_cooling_centres",
    "build_unified_action_plan",
    "save_actions_csv",
]
