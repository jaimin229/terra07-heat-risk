"""Configuration loader and validator for HeatLens (Team TERRA07)."""

from pathlib import Path
from typing import Dict, List, Any
import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class SeasonConfig(BaseModel):
    months: List[int]
    years: List[int]


class LandsatConfig(BaseModel):
    max_cloud_cover: float = 15.0
    min_scenes: int = 4


class ComponentWeights(BaseModel):
    hazard: float = 0.35
    exposure: float = 0.25
    vulnerability: float = 0.25
    adaptive_gap: float = 0.15


class HazardWeights(BaseModel):
    lst: float = 0.60
    building_coverage: float = 0.20
    veg_deficit: float = 0.20


class ExposureWeights(BaseModel):
    pop_density: float = 0.60
    outdoor_activity_proxy: float = 0.40


class VulnerabilityWeights(BaseModel):
    elderly_share: float = 0.60
    child_share: float = 0.40


class AdaptiveGapWeights(BaseModel):
    dist_cooling_centre: float = 0.50
    dist_water_point: float = 0.50


class WeightsConfig(BaseModel):
    components: ComponentWeights = Field(default_factory=ComponentWeights)
    hazard: HazardWeights = Field(default_factory=HazardWeights)
    exposure: ExposureWeights = Field(default_factory=ExposureWeights)
    vulnerability: VulnerabilityWeights = Field(default_factory=VulnerabilityWeights)
    adaptive_gap: AdaptiveGapWeights = Field(default_factory=AdaptiveGapWeights)


class NormalisationConfig(BaseModel):
    winsor_low: float = 0.02
    winsor_high: float = 0.98


class AccessConfig(BaseModel):
    water_walk_m: float = 300.0
    cooling_walk_m: float = 1000.0


class TiersConfig(BaseModel):
    low: float = 25.0
    moderate: float = 50.0
    high: float = 75.0


class ShadeActionConfig(BaseModel):
    delta_ndvi: float = 0.10
    max_plantable_fraction: float = 0.30
    cost_inr_per_cell_per_0p1_ndvi: float = 1500000.0


class WaterActionConfig(BaseModel):
    k: int = 15
    cost_inr_per_point: float = 250000.0


class CoolingActionConfig(BaseModel):
    k: int = 8
    cost_inr_per_centre: float = 1200000.0


class ActionsConfig(BaseModel):
    shade: ShadeActionConfig = Field(default_factory=ShadeActionConfig)
    water: WaterActionConfig = Field(default_factory=WaterActionConfig)
    cooling: CoolingActionConfig = Field(default_factory=CoolingActionConfig)


class HeatLensConfig(BaseModel):
    city: str = "Ahmedabad"
    bbox: List[float] = [72.54, 22.99, 72.62, 23.06]
    grid_size_m: int = 250
    season: SeasonConfig
    landsat: LandsatConfig = Field(default_factory=LandsatConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    normalisation: NormalisationConfig = Field(default_factory=NormalisationConfig)
    access: AccessConfig = Field(default_factory=AccessConfig)
    tiers: TiersConfig = Field(default_factory=TiersConfig)
    actions: ActionsConfig = Field(default_factory=ActionsConfig)
    random_seed: int = 42


def load_config(path: Path | str = CONFIG_PATH) -> HeatLensConfig:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Configuration file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return HeatLensConfig(**data)
