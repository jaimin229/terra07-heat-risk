"""
TERRA07 Explainable AI (XAI) & Driver Breakdown Engine
Software Track: Heat-Risk Mapping at Human Scale
Agent 4: Explainable AI & Driver Breakdown Architect

This module provides complete transparency and mathematical explainability into
WHY a street segment, ward, or neighborhood has a specific heat risk score.

Key Capabilities:
1. Additive & Game-Theoretic Shapley Feature Attribution:
   - Exact point contributions and percentage shares for 7 core heat drivers:
     * Surface Temperature (T_surface)
     * Canopy & Vegetation Deficit (NDVI deficiency)
     * Built-up Impervious Surface (NDBI / Albedo)
     * Elderly & Child Demographics
     * Outdoor Worker Exposure
     * AC / Cooling Access Deficit
     * Lack of Shaded Infrastructure
   - Satisfies efficiency, symmetry, dummy player, and additivity axioms.
2. Natural Language Diagnostic Generator:
   - Produces crisp, publication-ready executive briefs:
     e.g., "Ward 14 (Old Market Quarter) is rated EXTREME RISK (Score: 89.2).
     Primary driver: Extreme Surface Temperature (44.2°C, +34% contribution)
     combined with severe lack of tree canopy (NDVI 0.08, +26% contribution)
     and high density of outdoor market vendors (+22% contribution)."
3. Actionable Bottleneck Identification:
   - Identifies the #1 easiest leverage point to reduce risk in each zone.
   - Couples attribution points with intervention modifiability/feasibility.
   - Computes counterfactual score reductions and projected risk tiers.
4. Visualization-Ready Chart Data Formatters:
   - Waterfall chart data formatter (baseline -> feature increments -> total score).
   - Radar chart data formatter (7 normalized axes with benchmarks & safe thresholds).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union


# ============================================================================
# 1. ENUMS & CORE CONSTANTS
# ============================================================================

class HeatRiskDriver(str, Enum):
    """
    The 7 core biophysical, demographic, and built-environment drivers of urban heat risk.
    """
    SURFACE_TEMP = "surface_temp"
    CANOPY_DEFICIT = "canopy_deficit"
    IMPERVIOUS_SURFACE = "impervious_surface"
    DEMOGRAPHIC_VULNERABILITY = "demographic_vulnerability"
    OUTDOOR_WORKERS = "outdoor_workers"
    COOLING_DEFICIT = "cooling_deficit"
    SHADE_DEFICIT = "shade_deficit"

    @property
    def display_name(self) -> str:
        names = {
            HeatRiskDriver.SURFACE_TEMP: "Surface Temperature (T_surface)",
            HeatRiskDriver.CANOPY_DEFICIT: "Canopy & Vegetation Deficit (NDVI deficiency)",
            HeatRiskDriver.IMPERVIOUS_SURFACE: "Built-up Impervious Surface (NDBI / Low Albedo)",
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: "Elderly & Child Demographics",
            HeatRiskDriver.OUTDOOR_WORKERS: "Outdoor Worker Exposure",
            HeatRiskDriver.COOLING_DEFICIT: "AC / Cooling Access Deficit",
            HeatRiskDriver.SHADE_DEFICIT: "Lack of Shaded Infrastructure",
        }
        return names[self]

    @property
    def category(self) -> str:
        """IPCC AR6 Risk Component category."""
        categories = {
            HeatRiskDriver.SURFACE_TEMP: "Hazard",
            HeatRiskDriver.CANOPY_DEFICIT: "Vulnerability / Environmental",
            HeatRiskDriver.IMPERVIOUS_SURFACE: "Hazard / Built Fabric",
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: "Vulnerability / Sensitivity",
            HeatRiskDriver.OUTDOOR_WORKERS: "Exposure / Occupational",
            HeatRiskDriver.COOLING_DEFICIT: "Adaptive Capacity Deficit",
            HeatRiskDriver.SHADE_DEFICIT: "Exposure / Microclimate Deficit",
        }
        return categories[self]

    @property
    def unit_label(self) -> str:
        units = {
            HeatRiskDriver.SURFACE_TEMP: "°C",
            HeatRiskDriver.CANOPY_DEFICIT: "deficit index",
            HeatRiskDriver.IMPERVIOUS_SURFACE: "NDBI index",
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: "%",
            HeatRiskDriver.OUTDOOR_WORKERS: "%",
            HeatRiskDriver.COOLING_DEFICIT: "%",
            HeatRiskDriver.SHADE_DEFICIT: "% unshaded",
        }
        return units[self]

    @property
    def hex_color(self) -> str:
        """Visual color coding for charts and UI badges."""
        colors = {
            HeatRiskDriver.SURFACE_TEMP: "#E63946",       # Thermal Red
            HeatRiskDriver.CANOPY_DEFICIT: "#F4A261",     # Canopy Sand / Coral
            HeatRiskDriver.IMPERVIOUS_SURFACE: "#6C757D", # Impervious Slate Gray
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: "#9B5DE5", # Lavender / Purple
            HeatRiskDriver.OUTDOOR_WORKERS: "#E76F51",    # Brick Orange
            HeatRiskDriver.COOLING_DEFICIT: "#00B4D8",    # Deficit Cyan / Sky
            HeatRiskDriver.SHADE_DEFICIT: "#F77F00",      # Deep Amber
        }
        return colors[self]


class RiskTier(str, Enum):
    """Categorical risk rating tiers."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    EXTREME = "Extreme"

    @property
    def color_hex(self) -> str:
        colors = {
            RiskTier.LOW: "#2ECC71",       # Green
            RiskTier.MODERATE: "#F1C40F",  # Yellow
            RiskTier.HIGH: "#E67E22",      # Orange
            RiskTier.SEVERE: "#E74C3C",    # Crimson
            RiskTier.EXTREME: "#8E44AD",   # Dark Purple
        }
        return colors[self]


def categorize_score(score: float) -> RiskTier:
    """Classifies a 0-100 score into standard risk tiers."""
    if score < 25.0:
        return RiskTier.LOW
    elif score < 50.0:
        return RiskTier.MODERATE
    elif score < 70.0:
        return RiskTier.HIGH
    elif score < 85.0:
        return RiskTier.SEVERE
    else:
        return RiskTier.EXTREME


# ============================================================================
# 2. DATA SCHEMAS & VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class DriverWeights:
    """
    Calibrated weights for additive multi-criteria risk decomposition.
    Based on urban heat balance studies and IPCC AR6 risk framework.
    Weights must sum strictly to 1.0.
    """
    surface_temp: float = 0.25
    canopy_deficit: float = 0.18
    impervious_surface: float = 0.12
    demographic_vulnerability: float = 0.15
    outdoor_workers: float = 0.12
    cooling_deficit: float = 0.10
    shade_deficit: float = 0.08

    def __post_init__(self) -> None:
        total = (
            self.surface_temp
            + self.canopy_deficit
            + self.impervious_surface
            + self.demographic_vulnerability
            + self.outdoor_workers
            + self.cooling_deficit
            + self.shade_deficit
        )
        if not math.isclose(total, 1.0, rel_tol=1e-4):
            raise ValueError(f"DriverWeights must sum to 1.0, got {total:.4f}")

    def get_weight(self, driver: HeatRiskDriver) -> float:
        mapping = {
            HeatRiskDriver.SURFACE_TEMP: self.surface_temp,
            HeatRiskDriver.CANOPY_DEFICIT: self.canopy_deficit,
            HeatRiskDriver.IMPERVIOUS_SURFACE: self.impervious_surface,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: self.demographic_vulnerability,
            HeatRiskDriver.OUTDOOR_WORKERS: self.outdoor_workers,
            HeatRiskDriver.COOLING_DEFICIT: self.cooling_deficit,
            HeatRiskDriver.SHADE_DEFICIT: self.shade_deficit,
        }
        return mapping[driver]


@dataclass(frozen=True)
class NormalizationThresholds:
    """
    Biophysical min/max bounds for rescaling raw values into normalized [0.0, 1.0] severity scores.
    """
    surface_temp_min_c: float = 24.0      # Baseline comfortable surface temp (°C)
    surface_temp_max_c: float = 52.0      # Extreme ground thermal radiation (°C)

    ndvi_green_benchmark: float = 0.40    # Healthy dense vegetative canopy NDVI
    ndvi_barren_min: float = 0.00         # Zero vegetation

    ndbi_vegetated_min: float = -0.30     # Water / dense vegetative cover
    ndbi_dense_concrete_max: float = 0.60 # Dense impervious built fabric

    demographics_min_pct: float = 0.0     # 0% combined elderly & young
    demographics_max_pct: float = 35.0    # 35% combined elderly & young

    outdoor_workers_min_pct: float = 0.0  # 0% outdoor labor force
    outdoor_workers_max_pct: float = 35.0 # 35% outdoor labor concentration

    cooling_deficit_min_pct: float = 0.0  # 0% unconditioned / AC deficit
    cooling_deficit_max_pct: float = 100.0# 100% unconditioned / AC deficit

    shade_deficit_min_pct: float = 0.0    # Fully shaded corridor
    shade_deficit_max_pct: float = 100.0  # 100% unshaded solar exposure


@dataclass
class RawDriverValues:
    """Raw observations or inputs for a specific spatial unit."""
    surface_temp_c: float
    ndvi: float
    ndbi: float
    demographics_vulnerable_pct: float
    outdoor_workers_pct: float
    cooling_deficit_pct: float
    shade_deficit_pct: float
    albedo: Optional[float] = None
    area_name: str = "Zone"
    zone_type: str = "ward"


@dataclass
class FeatureAttribution:
    """Detailed attribution metrics for an individual heat risk driver."""
    driver: HeatRiskDriver
    key: str
    display_name: str
    category: str
    raw_value: float
    raw_unit: str
    normalized_score: float                # 0.0 to 1.0 scale
    attribution_points: float              # Exact score points contributed (e.g. +30.3 pts)
    percentage_contribution: float         # Exact % share of total positive risk (0 to 100%)
    direction: str = "increasing_risk"     # "increasing_risk" or "protective"
    feasibility_rank: str = "Medium"       # "Immediate", "Rapid", "Medium", "Structural"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver": self.driver.value,
            "key": self.key,
            "display_name": self.display_name,
            "category": self.category,
            "raw_value": round(self.raw_value, 2),
            "raw_unit": self.raw_unit,
            "normalized_score": round(self.normalized_score, 4),
            "attribution_points": round(self.attribution_points, 2),
            "percentage_contribution": round(self.percentage_contribution, 1),
            "direction": self.direction,
            "feasibility_rank": self.feasibility_rank,
            "description": self.description,
            "color_hex": self.driver.hex_color,
        }


@dataclass
class BottleneckLeveragePoint:
    """Identified highest-leverage actionable intervention opportunity."""
    driver: HeatRiskDriver
    key: str
    display_name: str
    leverage_score: float                  # Combined impact * feasibility score
    intervention_name: str
    action_type: str
    feasibility_timeframe: str             # e.g., "Immediate (24-72h)", "Rapid (1-2 weeks)"
    estimated_cost_tier: str               # "Low", "Moderate", "Substantial"
    potential_score_reduction: float       # Counterfactual points reduced
    projected_new_score: float             # What-if risk score
    projected_new_tier: RiskTier           # What-if risk tier
    action_summary: str                    # Concise actionable directive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver": self.driver.value,
            "key": self.key,
            "display_name": self.display_name,
            "leverage_score": round(self.leverage_score, 2),
            "intervention_name": self.intervention_name,
            "action_type": self.action_type,
            "feasibility_timeframe": self.feasibility_timeframe,
            "estimated_cost_tier": self.estimated_cost_tier,
            "potential_score_reduction": round(self.potential_score_reduction, 1),
            "projected_new_score": round(self.projected_new_score, 1),
            "projected_new_tier": self.projected_new_tier.value,
            "action_summary": self.action_summary,
        }


@dataclass
class WaterfallChartStep:
    """Single step in a Waterfall chart visualization."""
    label: str
    key: str
    delta: float                           # Step difference (+/-)
    cumulative: float                      # Running total
    percentage: float                      # % contribution
    raw_display: str                       # e.g. "44.2°C"
    color: str                             # Hex color
    step_type: str                         # "baseline", "increase", "decrease", "total"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "key": self.key,
            "delta": round(self.delta, 2),
            "cumulative": round(self.cumulative, 2),
            "percentage": round(self.percentage, 1),
            "raw_display": self.raw_display,
            "color": self.color,
            "step_type": self.step_type,
        }


@dataclass
class WaterfallChartData:
    """Complete dataset ready for frontend Waterfall chart rendering."""
    baseline_label: str
    baseline_value: float
    final_score: float
    steps: List[WaterfallChartStep]
    net_excess: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_label": self.baseline_label,
            "baseline_value": round(self.baseline_value, 2),
            "final_score": round(self.final_score, 2),
            "net_excess": round(self.net_excess, 2),
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class RadarAxis:
    """Single axis in a Radar / Spider chart."""
    axis: str
    key: str
    category: str
    zone_score: float                      # 0 to 100 scale for spider chart
    benchmark_average: float               # City average (0 to 100)
    safe_threshold: float                  # Target safe threshold (0 to 100)
    raw_value: float
    raw_unit: str
    raw_display: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axis": self.axis,
            "key": self.key,
            "category": self.category,
            "zone_score": round(self.zone_score, 1),
            "benchmark_average": round(self.benchmark_average, 1),
            "safe_threshold": round(self.safe_threshold, 1),
            "raw_value": round(self.raw_value, 2),
            "raw_unit": self.raw_unit,
            "raw_display": self.raw_display,
        }


@dataclass
class RadarChartData:
    """Complete dataset ready for frontend Radar chart rendering."""
    entity_id: str
    entity_name: str
    risk_score: float
    axes: List[RadarAxis]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "risk_score": round(self.risk_score, 1),
            "axes": [a.to_dict() for a in self.axes],
        }


@dataclass
class XAIDiagnosticReport:
    """
    Comprehensive Explainable AI Diagnostic Report for an assessed spatial entity.
    """
    entity_id: str
    entity_name: str
    entity_type: str                       # "ward", "street", "neighborhood", "custom"
    heat_risk_score: float                 # 0.0 to 100.0
    risk_tier: RiskTier
    methodology: str                       # "exact_additive" or "shapley_game_theoretic"
    baseline_reference_score: float
    risk_excess_above_baseline: float
    factor_attributions: List[FeatureAttribution]
    primary_driver: FeatureAttribution
    secondary_driver: FeatureAttribution
    tertiary_driver: FeatureAttribution
    executive_summary: str
    detailed_narrative: str
    top_leverage_bottleneck: BottleneckLeveragePoint
    all_leverage_opportunities: List[BottleneckLeveragePoint]
    waterfall_chart: WaterfallChartData
    radar_chart: RadarChartData
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "heat_risk_score": round(self.heat_risk_score, 1),
            "risk_tier": self.risk_tier.value,
            "color_hex": self.risk_tier.color_hex,
            "methodology": self.methodology,
            "baseline_reference_score": round(self.baseline_reference_score, 1),
            "risk_excess_above_baseline": round(self.risk_excess_above_baseline, 1),
            "factor_attributions": [f.to_dict() for f in self.factor_attributions],
            "primary_driver": self.primary_driver.to_dict(),
            "secondary_driver": self.secondary_driver.to_dict(),
            "tertiary_driver": self.tertiary_driver.to_dict(),
            "executive_summary": self.executive_summary,
            "detailed_narrative": self.detailed_narrative,
            "top_leverage_bottleneck": self.top_leverage_bottleneck.to_dict(),
            "all_leverage_opportunities": [b.to_dict() for b in self.all_leverage_opportunities],
            "waterfall_chart": self.waterfall_chart.to_dict(),
            "radar_chart": self.radar_chart.to_dict(),
            "metadata": self.metadata,
        }


# ============================================================================
# 3. INTERVENTION CATALOG & FEASIBILITY MATRIX
# ============================================================================

@dataclass(frozen=True)
class InterventionCatalogItem:
    """Catalog metadata for interventions addressing specific heat drivers."""
    driver: HeatRiskDriver
    intervention_name: str
    action_type: str
    feasibility_weight: float              # 0.0 to 1.0 (ease and immediacy of deployment)
    mitigation_efficiency: float           # Estimated % reduction in driver deficit (0.0 to 1.0)
    timeframe: str
    cost_tier: str
    action_template: str


INTERVENTION_CATALOG: Dict[HeatRiskDriver, InterventionCatalogItem] = {
    HeatRiskDriver.SHADE_DEFICIT: InterventionCatalogItem(
        driver=HeatRiskDriver.SHADE_DEFICIT,
        intervention_name="Rapid Tensile Shade Sails & Pop-up Canopies",
        action_type="Structural / Rapid Deployment",
        feasibility_weight=0.95,           # Easiest & fastest human-scale deployment
        mitigation_efficiency=0.65,        # Can eliminate 65% of pedestrian solar exposure
        timeframe="Immediate (24-72 hours)",
        cost_tier="Low",
        action_template=(
            "Deploy modular tensile shade sails along high-traffic walking corridors and transit stops, "
            "blocking direct beam solar irradiance and dropping mean radiant temperature by 8-12°C."
        ),
    ),
    HeatRiskDriver.COOLING_DEFICIT: InterventionCatalogItem(
        driver=HeatRiskDriver.COOLING_DEFICIT,
        intervention_name="Public Cooling Sanctuaries & Chilled Hydration Hubs",
        action_type="Operational / Civic Infrastructure",
        feasibility_weight=0.85,           # Very rapid activation of existing facilities
        mitigation_efficiency=0.55,        # Offsets 55% of indoor cooling deprivation
        timeframe="Rapid (24-48 hours)",
        cost_tier="Low",
        action_template=(
            "Activate municipal libraries, civic centers, and metro concourses as 24/7 air-conditioned refuges, "
            "coupled with refrigerated water distribution points at key neighborhood nodes."
        ),
    ),
    HeatRiskDriver.OUTDOOR_WORKERS: InterventionCatalogItem(
        driver=HeatRiskDriver.OUTDOOR_WORKERS,
        intervention_name="Workplace Thermal Safety Shifts & Mobile Misting Stations",
        action_type="Regulatory & Mobile Health",
        feasibility_weight=0.80,           # High feasibility via policy & mobile units
        mitigation_efficiency=0.50,        # Reduces active occupational heat load by 50%
        timeframe="Immediate (12-24 hours)",
        cost_tier="Low",
        action_template=(
            "Enforce mandatory midday work pauses (12:00-16:00), deploy mobile misting hydration buses, "
            "and distribute electrolyte replenishment packets to street vendors and construction laborers."
        ),
    ),
    HeatRiskDriver.IMPERVIOUS_SURFACE: InterventionCatalogItem(
        driver=HeatRiskDriver.IMPERVIOUS_SURFACE,
        intervention_name="High-Albedo Cool Roof Whitewashing & Reflective Pavements",
        action_type="Surface Retrofit",
        feasibility_weight=0.65,           # Highly effective medium-scale retrofit
        mitigation_efficiency=0.45,        # Reflects 45% of sensible heat absorption
        timeframe="Short-term (1-3 weeks)",
        cost_tier="Moderate",
        action_template=(
            "Apply high-solar-reflectance (SRI > 80) elastomeric coatings on tin and flat roofs, "
            "preventing sensible heat trapping and lowering indoor temperatures by 2.5-4.0°C."
        ),
    ),
    HeatRiskDriver.CANOPY_DEFICIT: InterventionCatalogItem(
        driver=HeatRiskDriver.CANOPY_DEFICIT,
        intervention_name="Dense Miyawaki Urban Forestry & Vegetative Bioswales",
        action_type="Nature-Based Infrastructure",
        feasibility_weight=0.45,           # Longer maturation, medium-term feasibility
        mitigation_efficiency=0.40,        # Deep long-term microclimate transformation
        timeframe="Medium-term (1-3 seasons)",
        cost_tier="Moderate",
        action_template=(
            "Establish rapid-growth micro-forests and continuous tree canopies along rights-of-way, "
            "providing lasting evapotranspirative cooling and particulate filtration."
        ),
    ),
    HeatRiskDriver.SURFACE_TEMP: InterventionCatalogItem(
        driver=HeatRiskDriver.SURFACE_TEMP,
        intervention_name="Evaporative Road Misting & Strategic Permeable Pavements",
        action_type="Microclimate Thermal Mitigation",
        feasibility_weight=0.50,
        mitigation_efficiency=0.35,
        timeframe="Short-term (3-7 days)",
        cost_tier="Moderate",
        action_template=(
            "Deploy localized road surface cooling sprinklers using non-potable recycled water during peak hours "
            "and replace degraded asphalt with light-colored permeable paving."
        ),
    ),
    HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: InterventionCatalogItem(
        driver=HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY,
        intervention_name="Proactive Community Elder & Child Heat-Health Outreach",
        action_type="Targeted Public Health Care",
        feasibility_weight=0.70,           # High social care feasibility
        mitigation_efficiency=0.40,
        timeframe="Immediate (24 hours)",
        cost_tier="Low",
        action_template=(
            "Dispatch community health workers (ASHAs / paramedics) for daily welfare checks, provide fans "
            "and oral rehydration solutions to isolated seniors, and ensure pediatric clinics have backup power."
        ),
    ),
}


# ============================================================================
# 4. NORMALIZATION & PREPROCESSING UTILITIES
# ============================================================================

def clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamps a floating-point value to [low, high]."""
    return max(low, min(high, float(val)))


def normalize_driver_value(
    driver: HeatRiskDriver,
    raw_val: float,
    thresholds: Optional[NormalizationThresholds] = None,
) -> float:
    """
    Normalizes raw biophysical or socio-demographic indicators to [0.0, 1.0] severity scores.
    0.0 represents zero heat risk contribution (optimal conditions).
    1.0 represents maximal heat risk severity.
    """
    t = thresholds or NormalizationThresholds()

    if driver == HeatRiskDriver.SURFACE_TEMP:
        # Higher surface temp = higher risk
        scaled = (raw_val - t.surface_temp_min_c) / (t.surface_temp_max_c - t.surface_temp_min_c)
        return clamp(scaled)

    elif driver == HeatRiskDriver.CANOPY_DEFICIT:
        # raw_val can be NDVI or direct deficit
        # If raw_val is NDVI (typically -0.1 to +0.8), higher NDVI means MORE green, so deficit is (benchmark - ndvi)
        if raw_val <= 1.0 and raw_val >= -0.5:
            # Interpreted as NDVI
            deficit = (t.ndvi_green_benchmark - raw_val) / t.ndvi_green_benchmark
            return clamp(deficit)
        else:
            # Interpreted as direct deficit percentage (0 - 100)
            return clamp(raw_val / 100.0)

    elif driver == HeatRiskDriver.IMPERVIOUS_SURFACE:
        # raw_val can be NDBI index (-0.3 to 0.6) or built-up percentage (0 to 100)
        if -1.0 <= raw_val <= 1.0:
            scaled = (raw_val - t.ndbi_vegetated_min) / (t.ndbi_dense_concrete_max - t.ndbi_vegetated_min)
            return clamp(scaled)
        else:
            return clamp(raw_val / 100.0)

    elif driver == HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY:
        scaled = (raw_val - t.demographics_min_pct) / (t.demographics_max_pct - t.demographics_min_pct)
        return clamp(scaled)

    elif driver == HeatRiskDriver.OUTDOOR_WORKERS:
        scaled = (raw_val - t.outdoor_workers_min_pct) / (t.outdoor_workers_max_pct - t.outdoor_workers_min_pct)
        return clamp(scaled)

    elif driver == HeatRiskDriver.COOLING_DEFICIT:
        scaled = (raw_val - t.cooling_deficit_min_pct) / (t.cooling_deficit_max_pct - t.cooling_deficit_min_pct)
        return clamp(scaled)

    elif driver == HeatRiskDriver.SHADE_DEFICIT:
        # raw_val is unshaded deficit percentage [0.0 - 100.0]
        scaled = (raw_val - t.shade_deficit_min_pct) / (t.shade_deficit_max_pct - t.shade_deficit_min_pct)
        return clamp(scaled)

    return 0.0


def parse_raw_inputs(data: Union[Dict[str, Any], RawDriverValues, Any]) -> Tuple[Dict[HeatRiskDriver, float], Dict[HeatRiskDriver, float]]:
    """
    Robustly extracts and normalizes the 7 heat drivers from arbitrary dicts,
    dataclasses, pandas Series, or backend entity records.
    Returns (raw_values_dict, normalized_values_dict).
    """
    if isinstance(data, RawDriverValues):
        raws = {
            HeatRiskDriver.SURFACE_TEMP: data.surface_temp_c,
            HeatRiskDriver.CANOPY_DEFICIT: data.ndvi,
            HeatRiskDriver.IMPERVIOUS_SURFACE: data.ndbi,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: data.demographics_vulnerable_pct,
            HeatRiskDriver.OUTDOOR_WORKERS: data.outdoor_workers_pct,
            HeatRiskDriver.COOLING_DEFICIT: data.cooling_deficit_pct,
            HeatRiskDriver.SHADE_DEFICIT: data.shade_deficit_pct,
        }
    elif isinstance(data, dict):
        d = data.copy()
        env = d.get("environmental", {}) if isinstance(d.get("environmental"), dict) else {}
        demo = d.get("demographics", {}) if isinstance(d.get("demographics"), dict) else {}
        adapt = d.get("adaptive_capacity", {}) if isinstance(d.get("adaptive_capacity"), dict) else {}

        # 1. Surface Temp (°C)
        st_candidates = [
            d.get("surface_temp"), d.get("surface_temp_c"), d.get("lst"), d.get("mean_lst_celsius"),
            d.get("mean_radiant_temp_celsius"), d.get("lst_c"), env.get("mean_lst_celsius"),
            d.get("temperature"), 42.0
        ]
        st_val = float(next(v for v in st_candidates if v is not None))

        # 2. Canopy / Vegetation Deficit (NDVI or %)
        ndvi_candidates = [
            d.get("ndvi"), d.get("ndvi_vegetation_index"), env.get("ndvi_vegetation_index"),
            d.get("tree_canopy_pct"), env.get("tree_canopy_pct"), d.get("canopy_deficit"),
            0.15
        ]
        ndvi_val = float(next(v for v in ndvi_candidates if v is not None))

        # 3. Built-up Impervious Surface (NDBI or %)
        ndbi_candidates = [
            d.get("ndbi"), d.get("ndbi_builtup_index"), env.get("ndbi_builtup_index"),
            d.get("impervious_surface_pct"), env.get("impervious_surface_pct"),
            d.get("impervious_surface"), 0.45
        ]
        ndbi_val = float(next(v for v in ndbi_candidates if v is not None))

        # 4. Demographic Vulnerability (Elderly + Children %)
        eld_cand = next((v for v in [d.get("elderly_pct"), demo.get("elderly_pct")] if v is not None), 12.0)
        chi_cand = next((v for v in [d.get("child_pct"), d.get("children_pct"), demo.get("children_pct")] if v is not None), 8.0)
        demo_combined = float(eld_cand) + float(chi_cand)

        # 5. Outdoor Workers Exposure (%)
        labor_candidates = [
            d.get("outdoor_workers_pct"), d.get("labor_pct"), demo.get("outdoor_workers_pct"),
            demo.get("outdoor_laborers_count"), 20.0
        ]
        labor_val = float(next(v for v in labor_candidates if v is not None and not isinstance(v, bool)))
        if labor_val > 100.0:
            labor_val = 22.0  # fallback if count was passed instead of pct

        # 6. AC / Cooling Deficit (%)
        # Check if ac_penetration is given (deficit = 100 - ac_penetration)
        ac_pen = next((v for v in [d.get("ac_pct"), adapt.get("ac_penetration_pct")] if v is not None), None)
        if ac_pen is not None:
            ac_deficit_val = max(0.0, 100.0 - float(ac_pen))
        else:
            ac_deficit_val = float(next((v for v in [d.get("cooling_deficit_pct"), d.get("ac_deficit_pct")] if v is not None), 55.0))

        # 7. Shade Deficit (%)
        shade_ratio = d.get("shade_ratio")
        tree_canopy = next((v for v in [d.get("tree_canopy_pct"), env.get("tree_canopy_pct")] if v is not None), None)
        if shade_ratio is not None:
            shade_deficit_val = max(0.0, (1.0 - float(shade_ratio)) * 100.0)
        elif tree_canopy is not None:
            shade_deficit_val = max(0.0, 100.0 - float(tree_canopy))
        else:
            shade_deficit_val = float(next((v for v in [d.get("shade_deficit_pct"), d.get("unshaded_pct")] if v is not None), 65.0))

        raws = {

            HeatRiskDriver.SURFACE_TEMP: st_val,
            HeatRiskDriver.CANOPY_DEFICIT: ndvi_val,
            HeatRiskDriver.IMPERVIOUS_SURFACE: ndbi_val,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: demo_combined,
            HeatRiskDriver.OUTDOOR_WORKERS: labor_val,
            HeatRiskDriver.COOLING_DEFICIT: ac_deficit_val,
            HeatRiskDriver.SHADE_DEFICIT: shade_deficit_val,
        }
    else:
        # Fallback for generic object with attributes
        raws = {
            HeatRiskDriver.SURFACE_TEMP: float(getattr(data, "surface_temp_c", getattr(data, "lst", 42.0))),
            HeatRiskDriver.CANOPY_DEFICIT: float(getattr(data, "ndvi", 0.15)),
            HeatRiskDriver.IMPERVIOUS_SURFACE: float(getattr(data, "ndbi", 0.45)),
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: float(getattr(data, "demographics_vulnerable_pct", 20.0)),
            HeatRiskDriver.OUTDOOR_WORKERS: float(getattr(data, "outdoor_workers_pct", 18.0)),
            HeatRiskDriver.COOLING_DEFICIT: float(getattr(data, "cooling_deficit_pct", 50.0)),
            HeatRiskDriver.SHADE_DEFICIT: float(getattr(data, "shade_deficit_pct", 60.0)),
        }

    norms = {driver: normalize_driver_value(driver, val) for driver, val in raws.items()}
    return raws, norms


# ============================================================================
# 5. CORE ATTRIBUTION ENGINES
# ============================================================================

class AdditiveAttributionEngine:
    """
    Exact Additive Feature Attribution Engine.
    Computes exact point and percentage contributions to a 0-100 composite risk score.

    Mathematics:
    ------------
    Given normalized indicator vector z = (z_1, ..., z_7) where z_i in [0, 1]
    and calibrated weights w = (w_1, ..., w_7) with sum(w_i) = 1.0:
        Score = 100 * sum_{i=1}^7 (w_i * z_i)
        Contribution_i = 100 * w_i * z_i
        Percentage_i = (Contribution_i / sum_{j=1}^7 Contribution_j) * 100%

    This provides 100% mathematical closure and exact transparency.
    """

    def __init__(
        self,
        weights: Optional[DriverWeights] = None,
        thresholds: Optional[NormalizationThresholds] = None,
    ) -> None:
        self.weights = weights or DriverWeights()
        self.thresholds = thresholds or NormalizationThresholds()

    def compute_score(self, normalized_values: Dict[HeatRiskDriver, float]) -> float:
        """Computes aggregate heat risk score [0.0 - 100.0]."""
        total = sum(
            self.weights.get_weight(driver) * clamp(normalized_values.get(driver, 0.0))
            for driver in HeatRiskDriver
        )
        return round(total * 100.0, 2)

    def attribute(
        self,
        raw_values: Dict[HeatRiskDriver, float],
        normalized_values: Dict[HeatRiskDriver, float],
        baseline_score: float = 35.0,
    ) -> List[FeatureAttribution]:
        """
        Calculates exact score contributions and percentage allocations for all 7 drivers.
        """
        attributions: List[FeatureAttribution] = []
        point_contributions: Dict[HeatRiskDriver, float] = {}

        for driver in HeatRiskDriver:
            norm_val = clamp(normalized_values.get(driver, 0.0))
            w = self.weights.get_weight(driver)
            pts = 100.0 * w * norm_val
            point_contributions[driver] = pts

        sum_pts = sum(point_contributions.values())
        total_for_pct = sum_pts if sum_pts > 0.0 else 1.0

        for driver in HeatRiskDriver:
            pts = point_contributions[driver]
            pct = (pts / total_for_pct) * 100.0
            raw_val = raw_values.get(driver, 0.0)
            norm_val = normalized_values.get(driver, 0.0)

            # Generate biophysical driver narrative
            desc = self._generate_driver_description(driver, raw_val, norm_val, pts, pct)

            # Assign feasibility rank
            feasibility = INTERVENTION_CATALOG[driver].timeframe.split()[0]

            attributions.append(
                FeatureAttribution(
                    driver=driver,
                    key=driver.value,
                    display_name=driver.display_name,
                    category=driver.category,
                    raw_value=raw_val,
                    raw_unit=driver.unit_label,
                    normalized_score=round(norm_val, 4),
                    attribution_points=round(pts, 2),
                    percentage_contribution=round(pct, 1),
                    direction="increasing_risk" if pts > 0.5 else "protective",
                    feasibility_rank=feasibility,
                    description=desc,
                )
            )

        # Sort descending by attribution points
        attributions.sort(key=lambda x: x.attribution_points, reverse=True)
        return attributions

    def _generate_driver_description(
        self,
        driver: HeatRiskDriver,
        raw_val: float,
        norm_val: float,
        pts: float,
        pct: float,
    ) -> str:
        """Produces contextual scientific descriptions for each driver."""
        if driver == HeatRiskDriver.SURFACE_TEMP:
            return (
                f"Radiant surface thermal emission of {raw_val:.1f}°C drives intense convective heating, "
                f"contributing +{pts:.1f} points ({pct:.1f}% of total risk)."
            )
        elif driver == HeatRiskDriver.CANOPY_DEFICIT:
            return (
                f"Severe vegetation deficit (NDVI {raw_val:.2f}) deprives the corridor of evaporative cooling and "
                f"leaf canopy shade, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        elif driver == HeatRiskDriver.IMPERVIOUS_SURFACE:
            return (
                f"High impervious built-up fraction (NDBI {raw_val:.2f}) stores sensible heat during the day and "
                f"amplifies nocturnal heat trapping, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        elif driver == HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY:
            return (
                f"{raw_val:.1f}% of the local population consists of seniors and young children with reduced "
                f"physiological thermoregulatory buffers, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        elif driver == HeatRiskDriver.OUTDOOR_WORKERS:
            return (
                f"{raw_val:.1f}% outdoor labor concentration (vendors, construction, gig delivery) exposed without "
                f"mechanical air conditioning, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        elif driver == HeatRiskDriver.COOLING_DEFICIT:
            return (
                f"{raw_val:.1f}% households lack air conditioning or accessible public cooling sanctuaries during "
                f"peak midday heat, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        elif driver == HeatRiskDriver.SHADE_DEFICIT:
            return (
                f"{raw_val:.1f}% unshaded pedestrian exposure allows unattenuated solar radiation to heat "
                f"walking surfaces and transit riders, contributing +{pts:.1f} points ({pct:.1f}%)."
            )
        return f"{driver.display_name} contributes {pts:.1f} points ({pct:.1f}%)."


class ShapleyAttributionEngine:
    """
    Game-Theoretic Shapley Value Decomposition Engine.
    Computes exact Shapley values across all 2^7 = 128 feature coalitions for
    any arbitrary scoring model f(x) -> float.

    Axiomatic Guarantees:
    ---------------------
    1. Efficiency: sum(phi_i) = f(x) - f(baseline)
    2. Symmetry: identical players receive identical attribution
    3. Dummy Player: players with zero marginal contribution receive 0.0
    4. Additivity: phi(f + g) = phi(f) + phi(g)
    """

    def __init__(
        self,
        model_func: Optional[Callable[[Dict[HeatRiskDriver, float]], float]] = None,
        baseline_values: Optional[Dict[HeatRiskDriver, float]] = None,
    ) -> None:
        self.model_func = model_func or self._default_multi_criteria_model
        self.baseline_values = baseline_values or {
            driver: 0.15 for driver in HeatRiskDriver
        }

    @staticmethod
    def _default_multi_criteria_model(features: Dict[HeatRiskDriver, float]) -> float:
        """
        Default non-linear geometric-additive risk model combining hazard, exposure, and vulnerability.
        Demonstrates non-linear Shapley interaction effects.
        """
        h = 0.6 * features.get(HeatRiskDriver.SURFACE_TEMP, 0.0) + 0.4 * features.get(HeatRiskDriver.IMPERVIOUS_SURFACE, 0.0)
        e = 0.5 * features.get(HeatRiskDriver.OUTDOOR_WORKERS, 0.0) + 0.5 * features.get(HeatRiskDriver.SHADE_DEFICIT, 0.0)
        v = (
            0.4 * features.get(HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY, 0.0)
            + 0.3 * features.get(HeatRiskDriver.COOLING_DEFICIT, 0.0)
            + 0.3 * features.get(HeatRiskDriver.CANOPY_DEFICIT, 0.0)
        )
        # Non-linear interaction: Risk = 100 * (0.45 * H + 0.35 * (E * V)^0.5 + 0.20 * V)
        score = 100.0 * (0.45 * h + 0.35 * math.sqrt(max(0.0, e * v)) + 0.20 * v)
        return round(clamp(score, 0.0, 100.0), 2)

    def compute_shapley_values(
        self,
        sample_values: Dict[HeatRiskDriver, float],
    ) -> Dict[HeatRiskDriver, float]:
        """
        Computes exact game-theoretic Shapley values using full coalition permutation enumeration.
        Size of feature set |N| = 7, so 2^7 = 128 subsets, computed in sub-millisecond time.
        """
        drivers = list(HeatRiskDriver)
        n = len(drivers)
        shapley_values: Dict[HeatRiskDriver, float] = {d: 0.0 for d in drivers}

        # Cache baseline model evaluation
        f_baseline = self.model_func(self.baseline_values)

        # Precompute subset evaluations for memoization
        subset_evals: Dict[Tuple[int, ...], float] = {}

        def get_eval(subset_indices: Tuple[int, ...]) -> float:
            if subset_indices in subset_evals:
                return subset_evals[subset_indices]
            config = {}
            for i, d in enumerate(drivers):
                if i in subset_indices:
                    config[d] = sample_values.get(d, 0.0)
                else:
                    config[d] = self.baseline_values.get(d, 0.0)
            val = self.model_func(config)
            subset_evals[subset_indices] = val
            return val

        # Exact Shapley formula:
        # phi_i = sum_{S subset N\{i}} (|S|! * (|N| - |S| - 1)! / |N|!) * [f(S U {i}) - f(S)]
        for i, driver in enumerate(drivers):
            other_indices = [idx for idx in range(n) if idx != i]
            phi_i = 0.0

            for s_size in range(n):
                weight = (math.factorial(s_size) * math.factorial(n - s_size - 1)) / math.factorial(n)
                for subset in itertools.combinations(other_indices, s_size):
                    val_without = get_eval(subset)
                    subset_with = tuple(sorted(subset + (i,)))
                    val_with = get_eval(subset_with)
                    marginal = val_with - val_without
                    phi_i += weight * marginal

            shapley_values[driver] = round(phi_i, 3)

        return shapley_values

    def attribute(
        self,
        raw_values: Dict[HeatRiskDriver, float],
        normalized_values: Dict[HeatRiskDriver, float],
    ) -> Tuple[float, float, List[FeatureAttribution]]:
        """
        Executes full Shapley decomposition and converts to FeatureAttribution items.
        """
        sample_score = self.model_func(normalized_values)
        base_score = self.model_func(self.baseline_values)
        shap_vals = self.compute_shapley_values(normalized_values)

        # Calculate positive sum for percentage distribution
        pos_sum = sum(max(0.0, v) for v in shap_vals.values())
        if pos_sum <= 0.0:
            pos_sum = 1.0

        attributions: List[FeatureAttribution] = []
        for driver in HeatRiskDriver:
            val = shap_vals[driver]
            pct = (max(0.0, val) / pos_sum) * 100.0 if val > 0 else 0.0
            raw = raw_values.get(driver, 0.0)
            norm = normalized_values.get(driver, 0.0)

            attributions.append(
                FeatureAttribution(
                    driver=driver,
                    key=driver.value,
                    display_name=driver.display_name,
                    category=driver.category,
                    raw_value=raw,
                    raw_unit=driver.unit_label,
                    normalized_score=round(norm, 4),
                    attribution_points=round(val, 2),
                    percentage_contribution=round(pct, 1),
                    direction="increasing_risk" if val > 0 else "protective",
                    feasibility_rank=INTERVENTION_CATALOG[driver].timeframe.split()[0],
                    description=(
                        f"Game-theoretic Shapley marginal contribution of {val:+.2f} points "
                        f"({pct:.1f}% share of positive risk escalation)."
                    ),
                )
            )

        attributions.sort(key=lambda x: x.attribution_points, reverse=True)
        return sample_score, base_score, attributions


# ============================================================================
# 6. NATURAL LANGUAGE DIAGNOSTIC GENERATOR
# ============================================================================

class DiagnosticNarrativeGenerator:
    """
    Generates crisp, publication-grade executive summaries and deep diagnostic
    syntheses for city decision-makers and municipal emergency teams.
    """

    @classmethod
    def generate_executive_summary(
        cls,
        entity_name: str,
        risk_score: float,
        risk_tier: RiskTier,
        top_drivers: Sequence[FeatureAttribution],
        zone_label: str = "Ward",
    ) -> str:
        """
        Produces the standard crisp executive summary matching the TERRA07 specification:
        e.g., "Ward 14 (Old Market Quarter) is rated EXTREME RISK (Score: 89.2).
        Primary driver: Extreme Surface Temperature (44.2°C, +34% contribution)
        combined with severe lack of tree canopy (NDVI 0.08, +26% contribution)
        and high density of outdoor market vendors (+22% contribution)."
        """
        if not top_drivers:
            return f"{zone_label} {entity_name} is rated {risk_tier.value.upper()} RISK (Score: {risk_score:.1f})."

        d1 = top_drivers[0]
        d2 = top_drivers[1] if len(top_drivers) > 1 else None
        d3 = top_drivers[2] if len(top_drivers) > 2 else None

        # Build natural driver labels with value & unit
        d1_text = cls._format_driver_summary_phrase(d1)

        summary_parts = [
            f"{zone_label} {entity_name} is rated {risk_tier.value.upper()} RISK (Score: {risk_score:.1f}).",
            f"Primary driver: {d1_text}"
        ]

        if d2 and d3:
            d2_text = cls._format_driver_summary_phrase(d2, lowercase_lead=True)
            d3_text = cls._format_driver_summary_phrase(d3, lowercase_lead=True)
            summary_parts.append(f"combined with {d2_text} and {d3_text}.")
        elif d2:
            d2_text = cls._format_driver_summary_phrase(d2, lowercase_lead=True)
            summary_parts.append(f"combined with {d2_text}.")
        else:
            summary_parts.append(".")

        return " ".join(summary_parts)

    @classmethod
    def _format_driver_summary_phrase(
        cls,
        attr: FeatureAttribution,
        lowercase_lead: bool = False,
    ) -> str:
        """Creates concise, evocative driver descriptions with values and contribution percentages."""
        driver = attr.driver
        raw = attr.raw_value
        pct = attr.percentage_contribution

        if driver == HeatRiskDriver.SURFACE_TEMP:
            lead = "extreme surface temperature" if lowercase_lead else "Extreme Surface Temperature"
            return f"{lead} ({raw:.1f}°C, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.CANOPY_DEFICIT:
            lead = "severe lack of tree canopy" if lowercase_lead else "Severe Lack of Tree Canopy"
            val_str = f"NDVI {raw:.2f}" if raw <= 1.0 else f"{raw:.0f}% deficit"
            return f"{lead} ({val_str}, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.IMPERVIOUS_SURFACE:
            lead = "high density of built-up impervious surfaces" if lowercase_lead else "High Built-up Impervious Surface"
            val_str = f"NDBI {raw:.2f}" if raw <= 1.0 else f"{raw:.0f}% impervious"
            return f"{lead} ({val_str}, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY:
            lead = "elevated elderly and child population vulnerability" if lowercase_lead else "High Elderly & Child Demographic Sensitivity"
            return f"{lead} ({raw:.1f}%, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.OUTDOOR_WORKERS:
            lead = "high density of outdoor market vendors and laborers" if lowercase_lead else "High Outdoor Worker Exposure"
            return f"{lead} ({raw:.1f}%, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.COOLING_DEFICIT:
            lead = "severe deficit in residential air conditioning and cooling access" if lowercase_lead else "AC & Cooling Access Deficit"
            return f"{lead} ({raw:.1f}%, +{pct:.0f}% contribution)"

        elif driver == HeatRiskDriver.SHADE_DEFICIT:
            lead = "critical lack of shaded pedestrian infrastructure" if lowercase_lead else "Lack of Shaded Infrastructure"
            return f"{lead} ({raw:.1f}% unshaded, +{pct:.0f}% contribution)"

        return f"{attr.display_name} ({raw:.1f} {attr.raw_unit}, +{pct:.0f}% contribution)"

    @classmethod
    def generate_detailed_narrative(
        cls,
        entity_name: str,
        risk_score: float,
        risk_tier: RiskTier,
        attributions: Sequence[FeatureAttribution],
        top_bottleneck: BottleneckLeveragePoint,
        zone_label: str = "Ward",
    ) -> str:
        """
        Generates an in-depth multi-paragraph diagnostic assessment suitable for
        city council briefings and public health incident command.
        """
        top3 = attributions[:3]
        d1, d2, d3 = top3[0], top3[1], top3[2]

        p1 = (
            f"Diagnostic Overview: {zone_label} {entity_name} recorded a Composite Heat Risk Index of "
            f"{risk_score:.1f}/100, placing it in the {risk_tier.value.upper()} danger tier. "
            f"Multi-criteria XAI decomposition reveals that the localized thermal crisis is predominantly "
            f"fueled by {d1.display_name} (contributing {d1.attribution_points:.1f} points, "
            f"or {d1.percentage_contribution:.1f}% of total risk points). "
            f"This is compounded by {d2.display_name} ({d2.attribution_points:.1f} pts, {d2.percentage_contribution:.1f}%) "
            f"and {d3.display_name} ({d3.attribution_points:.1f} pts, {d3.percentage_contribution:.1f}%)."
        )

        p2 = (
            f"Biophysical & Social Mechanism: Satellite thermal radiometry recorded surface temperatures of "
            f"{attributions[0].raw_value if attributions[0].driver == HeatRiskDriver.SURFACE_TEMP else 'elevated levels'} "
            f"over unshaded paved surfaces. The simultaneous presence of high demographic vulnerability and "
            f"outdoor workforce exposure creates an acute public health hazard, significantly increasing the probability "
            f"of severe heat exhaustion and non-compensable core body temperature spikes."
        )

        p3 = (
            f"Actionable Leverage Directive: The #1 easiest leverage point to lower immediate heat risk in {entity_name} "
            f"is '{top_bottleneck.intervention_name}' (Target: {top_bottleneck.display_name}). "
            f"Because this intervention boasts high deployment feasibility ({top_bottleneck.feasibility_timeframe}) and "
            f"substantial mitigation potency, executing it will reduce the risk score by an estimated "
            f"{top_bottleneck.potential_score_reduction:.1f} points, driving the overall score down to "
            f"{top_bottleneck.projected_new_score:.1f} ({top_bottleneck.projected_new_tier.value} Risk)."
        )

        return "\n\n".join([p1, p2, p3])


# ============================================================================
# 7. ACTIONABLE BOTTLENECK IDENTIFIER & COUNTERFACTUAL WHAT-IF
# ============================================================================

class BottleneckLeverageIdentifier:
    """
    Identifies the #1 easiest leverage point to reduce risk in each zone by evaluating
    the trade-off between attribution magnitude (impact) and intervention modifiability (ease).

    Mathematical Formulation:
    -------------------------
    For each driver k:
        Impact_k = AttributionPoints_k
        Feasibility_k = FeasibilityWeight_k in [0.0, 1.0] (from INTERVENTION_CATALOG)
        Efficiency_k = MitigationEfficiency_k in [0.0, 1.0]

        LeverageScore_k = Impact_k * Feasibility_k * Efficiency_k

    The driver with max(LeverageScore_k) is crowned the #1 Actionable Bottleneck.
    The Counterfactual Projected Risk Score is:
        Score_reduction = AttributionPoints_k * Efficiency_k
        New_Score = max(0.0, CurrentScore - Score_reduction)
    """

    @classmethod
    def evaluate_all_leverage_points(
        cls,
        current_score: float,
        attributions: Sequence[FeatureAttribution],
    ) -> List[BottleneckLeveragePoint]:
        """Ranks all 7 drivers by their actionable intervention leverage."""
        results: List[BottleneckLeveragePoint] = []

        for attr in attributions:
            catalog_item = INTERVENTION_CATALOG.get(attr.driver)
            if not catalog_item:
                continue

            impact = max(0.0, attr.attribution_points)
            feasibility = catalog_item.feasibility_weight
            efficiency = catalog_item.mitigation_efficiency

            leverage_score = impact * feasibility * efficiency
            score_reduction = round(impact * efficiency, 1)
            new_score = round(max(0.0, current_score - score_reduction), 1)
            new_tier = categorize_score(new_score)

            summary = catalog_item.action_template

            results.append(
                BottleneckLeveragePoint(
                    driver=attr.driver,
                    key=attr.key,
                    display_name=attr.display_name,
                    leverage_score=round(leverage_score, 2),
                    intervention_name=catalog_item.intervention_name,
                    action_type=catalog_item.action_type,
                    feasibility_timeframe=catalog_item.timeframe,
                    estimated_cost_tier=catalog_item.cost_tier,
                    potential_score_reduction=score_reduction,
                    projected_new_score=new_score,
                    projected_new_tier=new_tier,
                    action_summary=summary,
                )
            )

        # Sort descending by leverage score
        results.sort(key=lambda x: x.leverage_score, reverse=True)
        return results

    @classmethod
    def identify_primary_bottleneck(
        cls,
        current_score: float,
        attributions: Sequence[FeatureAttribution],
    ) -> BottleneckLeveragePoint:
        """Finds the #1 top leverage bottleneck."""
        rankings = cls.evaluate_all_leverage_points(current_score, attributions)
        return rankings[0]


# ============================================================================
# 8. VISUALIZATION-READY CHART FORMATTERS
# ============================================================================

class VisualizationDataFormatter:
    """
    Formats driver breakdowns into ready-to-render data structures for
    frontend Waterfall and Radar charts (compatible with Recharts, Plotly, Chart.js, D3).
    """

    @classmethod
    def build_waterfall_chart_data(
        cls,
        final_score: float,
        attributions: Sequence[FeatureAttribution],
        baseline_score: float = 0.0,
        baseline_label: str = "Base Score",
    ) -> WaterfallChartData:
        """
        Creates an ordered step-by-step Waterfall chart dataset.
        Shows how the score builds up from baseline through each factor contribution.
        """
        steps: List[WaterfallChartStep] = []
        running_total = baseline_score

        # Add initial baseline if baseline > 0
        if baseline_score > 0.0:
            steps.append(
                WaterfallChartStep(
                    label=baseline_label,
                    key="baseline",
                    delta=baseline_score,
                    cumulative=running_total,
                    percentage=0.0,
                    raw_display=f"{baseline_score:.1f} pts",
                    color="#4A5568",
                    step_type="baseline",
                )
            )

        # Add steps for each driver ordered by attribution
        for attr in attributions:
            delta = attr.attribution_points
            running_total += delta
            steps.append(
                WaterfallChartStep(
                    label=attr.display_name,
                    key=attr.key,
                    delta=round(delta, 2),
                    cumulative=round(running_total, 2),
                    percentage=round(attr.percentage_contribution, 1),
                    raw_display=f"{attr.raw_value:.1f} {attr.raw_unit}",
                    color=attr.driver.hex_color,
                    step_type="increase" if delta >= 0 else "decrease",
                )
            )

        # Add final total step
        tier = categorize_score(final_score)
        steps.append(
            WaterfallChartStep(
                label="Final Heat Risk Score",
                key="total",
                delta=0.0,
                cumulative=round(final_score, 2),
                percentage=100.0,
                raw_display=f"{final_score:.1f}/100",
                color=tier.color_hex,
                step_type="total",
            )
        )

        return WaterfallChartData(
            baseline_label=baseline_label,
            baseline_value=baseline_score,
            final_score=final_score,
            steps=steps,
            net_excess=round(final_score - baseline_score, 2),
        )

    @classmethod
    def build_radar_chart_data(
        cls,
        entity_id: str,
        entity_name: str,
        risk_score: float,
        attributions: Sequence[FeatureAttribution],
        city_benchmarks: Optional[Dict[HeatRiskDriver, float]] = None,
    ) -> RadarChartData:
        """
        Creates a 7-axis normalized (0-100) Radar/Spider chart dataset.
        Axes reflect the 7 core dimensions with citywide benchmark and safe target overlays.
        """
        # Default citywide benchmarks if not supplied
        default_benchmarks = {
            HeatRiskDriver.SURFACE_TEMP: 55.0,
            HeatRiskDriver.CANOPY_DEFICIT: 60.0,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 58.0,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 50.0,
            HeatRiskDriver.OUTDOOR_WORKERS: 48.0,
            HeatRiskDriver.COOLING_DEFICIT: 52.0,
            HeatRiskDriver.SHADE_DEFICIT: 56.0,
        }
        benchmarks = city_benchmarks or default_benchmarks

        # Safe environmental thresholds (e.g. recommended targets for resilient cities)
        safe_thresholds = {
            HeatRiskDriver.SURFACE_TEMP: 35.0,
            HeatRiskDriver.CANOPY_DEFICIT: 25.0,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 30.0,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 30.0,
            HeatRiskDriver.OUTDOOR_WORKERS: 25.0,
            HeatRiskDriver.COOLING_DEFICIT: 20.0,
            HeatRiskDriver.SHADE_DEFICIT: 20.0,
        }

        attr_map = {a.driver: a for a in attributions}
        axes: List[RadarAxis] = []

        # Order axes consistently clockwise
        axis_order = [
            HeatRiskDriver.SURFACE_TEMP,
            HeatRiskDriver.CANOPY_DEFICIT,
            HeatRiskDriver.IMPERVIOUS_SURFACE,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY,
            HeatRiskDriver.OUTDOOR_WORKERS,
            HeatRiskDriver.COOLING_DEFICIT,
            HeatRiskDriver.SHADE_DEFICIT,
        ]

        for driver in axis_order:
            attr = attr_map.get(driver)
            if not attr:
                continue

            zone_score = round(attr.normalized_score * 100.0, 1)
            bench = benchmarks.get(driver, 50.0)
            safe = safe_thresholds.get(driver, 25.0)

            axes.append(
                RadarAxis(
                    axis=driver.display_name.split("(")[0].strip(),
                    key=driver.value,
                    category=driver.category,
                    zone_score=zone_score,
                    benchmark_average=bench,
                    safe_threshold=safe,
                    raw_value=attr.raw_value,
                    raw_unit=attr.raw_unit,
                    raw_display=f"{attr.raw_value:.1f} {attr.raw_unit}",
                )
            )

        return RadarChartData(
            entity_id=entity_id,
            entity_name=entity_name,
            risk_score=risk_score,
            axes=axes,
        )


# ============================================================================
# 9. UNIFIED HIGH-LEVEL XAI ARCHITECT & EXPLAINER
# ============================================================================

class HeatRiskXAIExplainer:
    """
    Unified High-Level Explainability Orchestrator.
    Serves as the primary entry point for decomposing, diagnosing, and
    explaining heat risk across any ward, neighborhood, or street corridor.
    """

    def __init__(
        self,
        weights: Optional[DriverWeights] = None,
        thresholds: Optional[NormalizationThresholds] = None,
        baseline_score: float = 35.0,
    ) -> None:
        self.weights = weights or DriverWeights()
        self.thresholds = thresholds or NormalizationThresholds()
        self.baseline_score = baseline_score

        self.additive_engine = AdditiveAttributionEngine(
            weights=self.weights,
            thresholds=self.thresholds,
        )
        self.shapley_engine = ShapleyAttributionEngine()

    def explain(
        self,
        data: Union[Dict[str, Any], RawDriverValues, Any],
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        entity_type: str = "ward",
        methodology: str = "additive",     # "additive" or "shapley"
        target_score: Optional[float] = None,
    ) -> XAIDiagnosticReport:
        """
        Generates an end-to-end Explainable AI Diagnostic Report for an entity.

        Parameters
        ----------
        data : Dict[str, Any] or RawDriverValues
            Input dictionary or dataclass containing environmental, demographic,
            and built-environment metrics.
        entity_id : Optional[str]
            Identifier code (e.g. "W14", "ST102").
        entity_name : Optional[str]
            Human-readable name (e.g. "Old Market Quarter").
        entity_type : str
            Spatial category: "ward", "street", "neighborhood", or "custom".
        methodology : str
            "additive" (exact multi-criteria closed-form) or "shapley" (game-theoretic).
        target_score : Optional[float]
            If provided, scales or aligns attribution with an external model's composite score.

        Returns
        -------
        XAIDiagnosticReport
            Complete report with attributions, narrative, bottleneck, and chart formats.
        """
        # Resolve names and IDs
        if isinstance(data, dict):
            resolved_id = entity_id or data.get("ward_id") or data.get("street_id") or data.get("id") or "UNKNOWN_ID"
            resolved_name = entity_name or data.get("ward_name") or data.get("street_name") or data.get("name") or "Unnamed Zone"
            explicit_score = data.get("heat_risk_score") or data.get("pedestrian_heat_risk") or data.get("score")
        elif isinstance(data, RawDriverValues):
            resolved_id = entity_id or "ZONE_01"
            resolved_name = entity_name or data.area_name
            explicit_score = None
        else:
            resolved_id = entity_id or getattr(data, "entity_id", "ZONE_01")
            resolved_name = entity_name or getattr(data, "entity_name", getattr(data, "name", "Zone"))
            explicit_score = getattr(data, "hri", getattr(data, "heat_risk_score", None))

        # Parse and normalize inputs
        raw_values, norm_values = parse_raw_inputs(data)

        # Compute attribution
        if methodology.lower() == "shapley":
            calc_score, base_ref, attributions = self.shapley_engine.attribute(raw_values, norm_values)
            final_score = target_score or (float(explicit_score) if explicit_score is not None else calc_score)
            method_label = "shapley_game_theoretic"
        else:
            calc_score = self.additive_engine.compute_score(norm_values)
            final_score = target_score or (float(explicit_score) if explicit_score is not None else calc_score)
            base_ref = 0.0
            attributions = self.additive_engine.attribute(raw_values, norm_values, baseline_score=base_ref)
            method_label = "exact_additive"

            # If an external target score was provided, proportionally align attribution points
            if target_score is not None and not math.isclose(calc_score, target_score, abs_tol=0.1):
                scale = target_score / max(1.0, calc_score)
                for a in attributions:
                    a.attribution_points = round(a.attribution_points * scale, 2)

        final_score = round(clamp(final_score, 0.0, 100.0), 1)
        tier = categorize_score(final_score)

        # Identify top drivers
        primary = attributions[0]
        secondary = attributions[1] if len(attributions) > 1 else attributions[0]
        tertiary = attributions[2] if len(attributions) > 2 else attributions[0]

        # Natural language diagnostics
        zone_label = "Ward" if entity_type.lower() == "ward" else ("Street Segment" if entity_type.lower() == "street" else "Zone")
        exec_summary = DiagnosticNarrativeGenerator.generate_executive_summary(
            entity_name=resolved_name,
            risk_score=final_score,
            risk_tier=tier,
            top_drivers=attributions,
            zone_label=zone_label,
        )

        # Bottleneck identification
        all_bottlenecks = BottleneckLeverageIdentifier.evaluate_all_leverage_points(final_score, attributions)
        top_bottleneck = all_bottlenecks[0]

        detailed_narrative = DiagnosticNarrativeGenerator.generate_detailed_narrative(
            entity_name=resolved_name,
            risk_score=final_score,
            risk_tier=tier,
            attributions=attributions,
            top_bottleneck=top_bottleneck,
            zone_label=zone_label,
        )

        # Visualizations
        waterfall = VisualizationDataFormatter.build_waterfall_chart_data(
            final_score=final_score,
            attributions=attributions,
            baseline_score=base_ref,
        )
        radar = VisualizationDataFormatter.build_radar_chart_data(
            entity_id=resolved_id,
            entity_name=resolved_name,
            risk_score=final_score,
            attributions=attributions,
        )

        return XAIDiagnosticReport(
            entity_id=resolved_id,
            entity_name=resolved_name,
            entity_type=entity_type,
            heat_risk_score=final_score,
            risk_tier=tier,
            methodology=method_label,
            baseline_reference_score=base_ref,
            risk_excess_above_baseline=round(final_score - base_ref, 1),
            factor_attributions=attributions,
            primary_driver=primary,
            secondary_driver=secondary,
            tertiary_driver=tertiary,
            executive_summary=exec_summary,
            detailed_narrative=detailed_narrative,
            top_leverage_bottleneck=top_bottleneck,
            all_leverage_opportunities=all_bottlenecks,
            waterfall_chart=waterfall,
            radar_chart=radar,
            metadata={
                "calculated_additive_score": calc_score,
                "input_type": type(data).__name__,
            },
        )

    def batch_explain(
        self,
        records: Iterable[Union[Dict[str, Any], Any]],
        entity_type: str = "ward",
        methodology: str = "additive",
    ) -> List[XAIDiagnosticReport]:
        """Processes a collection of wards or streets in high-throughput batch mode."""
        reports: List[XAIDiagnosticReport] = []
        for r in records:
            rep = self.explain(r, entity_type=entity_type, methodology=methodology)
            reports.append(rep)
        return reports


# ============================================================================
# 10. CONVENIENCE SINGLETONS & MODULE-LEVEL ACCESSORS
# ============================================================================

_default_explainer = HeatRiskXAIExplainer()


def explain_heat_risk(
    data: Union[Dict[str, Any], RawDriverValues, Any],
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    entity_type: str = "ward",
    methodology: str = "additive",
    target_score: Optional[float] = None,
) -> XAIDiagnosticReport:
    """Convenience functional API to obtain an XAI diagnostic report."""
    return _default_explainer.explain(
        data=data,
        entity_id=entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
        methodology=methodology,
        target_score=target_score,
    )
