"""
Urban Heat Risk Assessment Engine (IPCC AR6 Framework)
Team: TERRA07 (Software Track: Heat-Risk Mapping at Human Scale)
Lead: Climate Risk Science Lead (Agent 1)

This module formalizes the Urban Heat Risk scoring formulation based on the
IPCC Sixth Assessment Report (AR6) Working Group II framework:
    Risk = f(Hazard, Exposure, Vulnerability)

The engine computes a Composite Heat Risk Index (HRI) scaled from 0 to 100,
supported by multi-criteria normalization, physical physiological thresholds
(e.g., 35°C wet bulb survivability limit, 42°C LST extreme danger), and
multi-scale spatial evaluation across both Ward/Grid zones and Street segments.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union


# ============================================================================
# 1. ENUMERATIONS & CORE TYPES
# ============================================================================

class RiskCategory(str, Enum):
    """
    Categorization of Heat Risk Index (HRI) based on standardized risk intervals:
    - Low: 0 - 25
    - Moderate: 26 - 50
    - High: 51 - 70
    - Severe: 71 - 85
    - Extreme: 86 - 100
    """
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    EXTREME = "Extreme"

    @property
    def color_hex(self) -> str:
        """Hex color code for map rendering and visual analytics."""
        colors = {
            RiskCategory.LOW: "#2ECC71",       # Emerald Green
            RiskCategory.MODERATE: "#F1C40F",  # Amber Yellow
            RiskCategory.HIGH: "#E67E22",      # Orange
            RiskCategory.SEVERE: "#E74C3C",    # Crimson Red
            RiskCategory.EXTREME: "#8E44AD",   # Dark Purple / Maroon
        }
        return colors[self]

    @property
    def public_health_action(self) -> str:
        """Standardized emergency and municipal intervention protocol."""
        actions = {
            RiskCategory.LOW: "Routine monitoring; maintain standard public hydration advisories.",
            RiskCategory.MODERATE: "Advisory alert; recommend shaded pedestrian corridors and voluntary cooling breaks.",
            RiskCategory.HIGH: "Amber alert; deploy mobile misting stations, extend park hours, issue outdoor worker warnings.",
            RiskCategory.SEVERE: "Red alert; activate designated municipal cooling shelters; enforce mandatory rest cycles for outdoor labor.",
            RiskCategory.EXTREME: "Emergency disaster declaration; cease non-essential outdoor work, deploy medical emergency teams, dispatch emergency water trucks.",
        }
        return actions[self]


# ============================================================================
# 2. CONFIGURATION & WEIGHT SPECIFICATIONS
# ============================================================================

@dataclass(frozen=True)
class HazardWeights:
    """Relative indicator weights for the Hazard sub-index (sum to 1.0)."""
    w_lst: float = 0.35              # Land Surface Temperature (°C)
    w_heat_index: float = 0.35       # Ambient air Heat Index (°C)
    w_ndbi: float = 0.15             # Normalized Difference Built-up Index
    w_solar_irradiance: float = 0.15 # Solar Irradiance (W/m²)

    def __post_init__(self) -> None:
        total = self.w_lst + self.w_heat_index + self.w_ndbi + self.w_solar_irradiance
        if not math.isclose(total, 1.0, rel_tol=1e-4):
            raise ValueError(f"HazardWeights must sum to 1.0, got {total:.4f}")


@dataclass(frozen=True)
class ExposureWeights:
    """Relative indicator weights for the Exposure sub-index (sum to 1.0)."""
    w_population_density: float = 0.40  # Residential & ambient population density
    w_pedestrian_traffic: float = 0.30  # Active outdoor pedestrian volume
    w_outdoor_workers: float = 0.30     # Construction, vendors, gig delivery workers

    def __post_init__(self) -> None:
        total = self.w_population_density + self.w_pedestrian_traffic + self.w_outdoor_workers
        if not math.isclose(total, 1.0, rel_tol=1e-4):
            raise ValueError(f"ExposureWeights must sum to 1.0, got {total:.4f}")


@dataclass(frozen=True)
class VulnerabilityWeights:
    """Relative indicator weights for the Vulnerability sub-index (sum to 1.0)."""
    w_elderly: float = 0.25              # Population aged > 65 years (%)
    w_children: float = 0.15             # Population aged < 5 years (%)
    w_ac_deficit: float = 0.25           # Low-income / AC deficit proportion (%)
    w_chronic_illness: float = 0.20      # Cardiovascular & respiratory disease prevalence (%)
    w_housing_vulnerability: float = 0.15# Uninsulated / tin / asbestos roofs (%)

    def __post_init__(self) -> None:
        total = (
            self.w_elderly
            + self.w_children
            + self.w_ac_deficit
            + self.w_chronic_illness
            + self.w_housing_vulnerability
        )
        if not math.isclose(total, 1.0, rel_tol=1e-4):
            raise ValueError(f"VulnerabilityWeights must sum to 1.0, got {total:.4f}")


@dataclass(frozen=True)
class NormalizationBounds:
    """
    Physical and empirical lower/upper bounds for min-max scaling into [0.0, 1.0].
    Values outside bounds are safely clamped.
    """
    # Hazard Bounds
    lst_min_c: float = 24.0           # Comfortable baseline LST (°C)
    lst_max_c: float = 52.0           # Extreme asphalt / bare earth LST (°C)
    heat_index_min_c: float = 25.0    # Thermally neutral heat index (°C)
    heat_index_max_c: float = 52.0    # Extreme danger threshold (°C)
    ndbi_min: float = -0.30           # Dense vegetated / water bodies
    ndbi_max: float = 0.60            # Dense impervious concrete / steel
    solar_min_w_m2: float = 200.0     # Diffuse / overcast solar irradiance
    solar_max_w_m2: float = 1050.0    # Peak summer unshaded global irradiance

    # Exposure Bounds
    pop_density_min: float = 0.0          # Uninhabited
    pop_density_max: float = 30000.0      # Ultra-dense urban core (persons/km²)
    pedestrian_traffic_min: float = 0.0    # Deserted street
    pedestrian_traffic_max: float = 1200.0 # High-density commercial pedestrian corridor (ped/hr)
    outdoor_workers_min_pct: float = 0.0  # 0% outdoor workforce
    outdoor_workers_max_pct: float = 35.0 # High concentration of informal/construction labor

    # Vulnerability Bounds
    elderly_min_pct: float = 0.0      # Min elderly demographic percentage
    elderly_max_pct: float = 30.0     # Max elderly demographic percentage
    children_min_pct: float = 0.0     # Min pediatric demographic percentage
    children_max_pct: float = 20.0    # Max pediatric demographic percentage
    ac_deficit_min_pct: float = 0.0   # 100% cooling access
    ac_deficit_max_pct: float = 100.0 # 0% cooling access
    chronic_illness_min_pct: float = 0.0
    chronic_illness_max_pct: float = 40.0 # Combined cardiovascular/respiratory morbidity
    housing_vuln_min_pct: float = 0.0
    housing_vuln_max_pct: float = 100.0


# ============================================================================
# 3. BIOPHYSICAL & METEOROLOGICAL UTILITIES
# ============================================================================

def calculate_heat_index(temp_c: float, rel_humidity: float) -> float:
    """
    Computes the NOAA / Steadman Heat Index in Celsius.
    Uses the full Rothfusz regression equation when T >= 26.7°C (80°F)
    and relative humidity >= 40%, falling back to simplified Steadman formula.

    Parameters
    ----------
    temp_c : float
        Dry-bulb ambient air temperature in degrees Celsius.
    rel_humidity : float
        Relative humidity percentage in range [0.0, 100.0].

    Returns
    -------
    float
        Heat index in degrees Celsius.
    """
    # Clamp relative humidity to valid meteorological range
    rh = max(0.0, min(100.0, rel_humidity))
    # Convert Celsius to Fahrenheit for NOAA polynomial
    tf = (temp_c * 9.0 / 5.0) + 32.0

    if tf < 75.0:
        # Below warm threshold, heat index is approximated by ambient temperature
        hi_f = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))
    else:
        # Rothfusz 9-parameter regression equation
        hi_f = (
            -42.379
            + 2.04901523 * tf
            + 10.14333127 * rh
            - 0.22475541 * tf * rh
            - 0.00683783 * tf * tf
            - 0.05481717 * rh * rh
            + 0.00122874 * tf * tf * rh
            + 0.00085282 * tf * rh * rh
            - 0.00000199 * tf * tf * rh * rh
        )

        # NOAA Adjustment for low humidity conditions
        if rh < 13.0 and 80.0 <= tf <= 112.0:
            adj = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(tf - 95.0)) / 17.0)
            hi_f -= adj
        # NOAA Adjustment for high humidity conditions
        elif rh > 85.0 and 80.0 <= tf <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
            hi_f += adj

    # Convert back to Celsius
    hi_c = (hi_f - 32.0) * 5.0 / 9.0
    return round(hi_c, 2)


def calculate_wet_bulb_temperature(temp_c: float, rel_humidity: float) -> float:
    """
    Computes Tw (Wet Bulb Temperature) in Celsius using Stull's (2011) empirical formula.
    Valid for standard atmospheric pressures and temperatures between -20°C and 50°C.

    Parameters
    ----------
    temp_c : float
        Dry-bulb ambient air temperature in degrees Celsius.
    rel_humidity : float
        Relative humidity percentage in range [0.0, 100.0].

    Returns
    -------
    float
        Wet bulb temperature in degrees Celsius.
    """
    t = temp_c
    rh = max(1.0, min(100.0, rel_humidity))

    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(tw, 2)


def min_max_scale(val: float, val_min: float, val_max: float) -> float:
    """
    Linearly scales a continuous value to [0.0, 1.0] with strict boundary clamping.
    """
    if val_max <= val_min:
        return 0.0
    scaled = (val - val_min) / (val_max - val_min)
    return max(0.0, min(1.0, float(scaled)))


# ============================================================================
# 4. INPUT SCHEMAS & DATA STRUCTURES
# ============================================================================

@dataclass
class HazardInputs:
    """
    Direct physical variables driving urban thermal hazard.

    Attributes
    ----------
    lst_c : float
        Land Surface Temperature (°C) from satellite thermal infrared sensors.
    heat_index_c : Optional[float]
        Direct ambient heat index (°C). If None, calculated via air_temp_c and relative_humidity.
    air_temp_c : Optional[float]
        Ambient dry-bulb air temperature (°C). Required if heat_index_c is None.
    relative_humidity : Optional[float]
        Relative humidity percentage [0-100]. Required if heat_index_c is None.
    ndbi : float
        Normalized Difference Built-up Index, representing impervious fraction [-1.0, 1.0].
    solar_irradiance_w_m2 : float
        Global horizontal solar irradiance in W/m² (range ~0 - 1100 W/m²).
    """
    lst_c: float
    ndbi: float
    solar_irradiance_w_m2: float
    heat_index_c: Optional[float] = None
    air_temp_c: Optional[float] = None
    relative_humidity: Optional[float] = None

    def resolve_heat_index(self) -> float:
        """Resolves or computes the ambient heat index."""
        if self.heat_index_c is not None:
            return float(self.heat_index_c)
        if self.air_temp_c is not None and self.relative_humidity is not None:
            return calculate_heat_index(self.air_temp_c, self.relative_humidity)
        raise ValueError(
            "HazardInputs must provide either 'heat_index_c' or both 'air_temp_c' and 'relative_humidity'."
        )

    def resolve_wet_bulb(self) -> Optional[float]:
        """Calculates wet bulb temperature if air temperature and RH are provided."""
        if self.air_temp_c is not None and self.relative_humidity is not None:
            return calculate_wet_bulb_temperature(self.air_temp_c, self.relative_humidity)
        return None


@dataclass
class ExposureInputs:
    """
    Variables measuring human presence in the thermal hazard footprint.

    Attributes
    ----------
    population_density_per_km2 : float
        Resident and ambient population density (people / km²).
    pedestrian_foot_traffic_hourly : float
        Hourly pedestrian volume count along streets / open areas (pedestrians / hr).
    outdoor_workers_pct : float
        Percentage of active workforce operating outdoors (delivery, construction, street vendors) [0-100].
    """
    population_density_per_km2: float
    pedestrian_foot_traffic_hourly: float
    outdoor_workers_pct: float


@dataclass
class VulnerabilityInputs:
    """
    Socioeconomic, demographic, and housing susceptibility factors.

    Attributes
    ----------
    elderly_pct : float
        Percentage of population aged 65 and older [0-100].
    children_pct : float
        Percentage of population under 5 years of age [0-100].
    ac_deficit_pct : float
        Percentage of households lacking mechanical air conditioning or unable to afford electricity [0-100].
    chronic_conditions_pct : float
        Prevalence rate of chronic cardiovascular and respiratory diseases [0-100].
    housing_uninsulated_pct : float
        Percentage of residential units with tin/uninsulated metal roofs or informal building materials [0-100].
    """
    elderly_pct: float
    children_pct: float
    ac_deficit_pct: float
    chronic_conditions_pct: float
    housing_uninsulated_pct: float


@dataclass
class WardRiskInput:
    """Input payload for Ward or Grid cell macro-scale scoring."""
    ward_id: str
    ward_name: str
    hazard: HazardInputs
    exposure: ExposureInputs
    vulnerability: VulnerabilityInputs
    area_sq_km: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreetSegmentRiskInput:
    """
    Input payload for Human-Scale Street Segment micro-scale scoring.

    Attributes
    ----------
    segment_id : str
        Unique OSM Way ID or street identifier.
    street_name : str
        Name of street or thoroughfare.
    hazard : HazardInputs
        Macro/meso hazard input for the corridor.
    exposure : ExposureInputs
        Corridor-specific exposure values.
    vulnerability : VulnerabilityInputs
        Intersecting neighborhood vulnerability characteristics.
    length_meters : float
        Length of street segment in meters.
    tree_canopy_pct : float
        Percentage of street canopy coverage [0-100]. High values provide radiative shade attenuation.
    canyon_aspect_ratio : float
        Street canyon height-to-width ratio (H/W). High ratios trap sensible heat at night.
    metadata : Dict[str, Any]
        Additional metadata (e.g. surface material, transit stop presence).
    """
    segment_id: str
    street_name: str
    hazard: HazardInputs
    exposure: ExposureInputs
    vulnerability: VulnerabilityInputs
    length_meters: float
    tree_canopy_pct: float = 0.0
    canyon_aspect_ratio: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 5. BREAKDOWN & RESULT SCHEMAS
# ============================================================================

@dataclass
class HazardBreakdown:
    """Detailed evaluation metrics for Hazard sub-index."""
    sub_index: float  # [0.0, 1.0]
    raw_lst_c: float
    norm_lst: float
    raw_heat_index_c: float
    norm_heat_index: float
    raw_ndbi: float
    norm_ndbi: float
    raw_solar_w_m2: float
    norm_solar: float
    wet_bulb_c: Optional[float] = None


@dataclass
class ExposureBreakdown:
    """Detailed evaluation metrics for Exposure sub-index."""
    sub_index: float  # [0.0, 1.0]
    raw_pop_density: float
    norm_pop_density: float
    raw_pedestrian_traffic: float
    norm_pedestrian_traffic: float
    raw_outdoor_workers_pct: float
    norm_outdoor_workers: float


@dataclass
class VulnerabilityBreakdown:
    """Detailed evaluation metrics for Vulnerability sub-index."""
    sub_index: float  # [0.0, 1.0]
    raw_elderly_pct: float
    norm_elderly: float
    raw_children_pct: float
    norm_children: float
    raw_ac_deficit_pct: float
    norm_ac_deficit: float
    raw_chronic_conditions_pct: float
    norm_chronic_conditions: float
    raw_housing_uninsulated_pct: float
    norm_housing_uninsulated: float


@dataclass
class HeatRiskScore:
    """
    Complete output score for an assessed spatial entity (Ward or Street).
    """
    entity_id: str
    entity_name: str
    entity_type: Literal["ward_grid", "street_segment"]
    hri: float  # Composite Heat Risk Index [0.0, 100.0]
    category: RiskCategory
    hazard_sub_index: float         # [0.0, 1.0]
    exposure_sub_index: float       # [0.0, 1.0]
    vulnerability_sub_index: float  # [0.0, 1.0]
    hazard_breakdown: HazardBreakdown
    exposure_breakdown: ExposureBreakdown
    vulnerability_breakdown: VulnerabilityBreakdown
    critical_flags: List[str] = field(default_factory=list)
    action_protocol: str = ""
    recommended_interventions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts result object to a clean JSON-serializable dictionary."""
        data = asdict(self)
        data["category"] = self.category.value
        data["color_hex"] = self.category.color_hex
        return data


# ============================================================================
# 6. URBAN HEAT RISK ENGINE (IPCC AR6 FORMULATION)
# ============================================================================

class UrbanHeatRiskEngine:
    """
    Production-grade Urban Heat Risk Calculation Engine implementing the
    IPCC AR6 Multi-Criteria Normalization framework.

    Formulation:
    ------------
    1. Multi-Criteria Rescaling:
       Each indicator x_i is normalized to s_i in [0, 1] using biophysical bounds.
    2. Sub-index aggregation:
       H = sum(w_h * s_h), E = sum(w_e * s_e), V = sum(w_v * s_v)
    3. Composite Risk Formulation:
       HRI = 100 * (H ^ alpha * E ^ beta * V ^ gamma)
       (Default: alpha = beta = gamma = 1/3, geometric mean preserving the zero-exposure axiom)
    """

    def __init__(
        self,
        hazard_weights: Optional[HazardWeights] = None,
        exposure_weights: Optional[ExposureWeights] = None,
        vulnerability_weights: Optional[VulnerabilityWeights] = None,
        bounds: Optional[NormalizationBounds] = None,
        aggregation_mode: Literal["geometric", "multiplicative_scaled", "arithmetic"] = "geometric",
    ) -> None:
        self.hazard_weights = hazard_weights or HazardWeights()
        self.exposure_weights = exposure_weights or ExposureWeights()
        self.vulnerability_weights = vulnerability_weights or VulnerabilityWeights()
        self.bounds = bounds or NormalizationBounds()
        self.aggregation_mode = aggregation_mode

    # ------------------------------------------------------------------------
    # SUB-INDEX CALCULATORS
    # ------------------------------------------------------------------------

    def compute_hazard_sub_index(self, inputs: HazardInputs) -> HazardBreakdown:
        """
        Computes normalized Hazard Sub-Index (H in [0.0, 1.0]).
        """
        raw_heat_index = inputs.resolve_heat_index()
        wet_bulb = inputs.resolve_wet_bulb()

        norm_lst = min_max_scale(inputs.lst_c, self.bounds.lst_min_c, self.bounds.lst_max_c)
        norm_hi = min_max_scale(raw_heat_index, self.bounds.heat_index_min_c, self.bounds.heat_index_max_c)
        norm_ndbi = min_max_scale(inputs.ndbi, self.bounds.ndbi_min, self.bounds.ndbi_max)
        norm_solar = min_max_scale(inputs.solar_irradiance_w_m2, self.bounds.solar_min_w_m2, self.bounds.solar_max_w_m2)

        # Weighted combination
        sub_index = (
            self.hazard_weights.w_lst * norm_lst
            + self.hazard_weights.w_heat_index * norm_hi
            + self.hazard_weights.w_ndbi * norm_ndbi
            + self.hazard_weights.w_solar_irradiance * norm_solar
        )
        sub_index = max(0.0, min(1.0, sub_index))

        return HazardBreakdown(
            sub_index=round(sub_index, 4),
            raw_lst_c=round(inputs.lst_c, 2),
            norm_lst=round(norm_lst, 4),
            raw_heat_index_c=round(raw_heat_index, 2),
            norm_heat_index=round(norm_hi, 4),
            raw_ndbi=round(inputs.ndbi, 3),
            norm_ndbi=round(norm_ndbi, 4),
            raw_solar_w_m2=round(inputs.solar_irradiance_w_m2, 1),
            norm_solar=round(norm_solar, 4),
            wet_bulb_c=wet_bulb,
        )

    def compute_exposure_sub_index(self, inputs: ExposureInputs) -> ExposureBreakdown:
        """
        Computes normalized Exposure Sub-Index (E in [0.0, 1.0]).
        """
        norm_pop = min_max_scale(
            inputs.population_density_per_km2,
            self.bounds.pop_density_min,
            self.bounds.pop_density_max,
        )
        norm_ped = min_max_scale(
            inputs.pedestrian_foot_traffic_hourly,
            self.bounds.pedestrian_traffic_min,
            self.bounds.pedestrian_traffic_max,
        )
        norm_workers = min_max_scale(
            inputs.outdoor_workers_pct,
            self.bounds.outdoor_workers_min_pct,
            self.bounds.outdoor_workers_max_pct,
        )

        sub_index = (
            self.exposure_weights.w_population_density * norm_pop
            + self.exposure_weights.w_pedestrian_traffic * norm_ped
            + self.exposure_weights.w_outdoor_workers * norm_workers
        )
        sub_index = max(0.0, min(1.0, sub_index))

        return ExposureBreakdown(
            sub_index=round(sub_index, 4),
            raw_pop_density=round(inputs.population_density_per_km2, 1),
            norm_pop_density=round(norm_pop, 4),
            raw_pedestrian_traffic=round(inputs.pedestrian_foot_traffic_hourly, 1),
            norm_pedestrian_traffic=round(norm_ped),
            raw_outdoor_workers_pct=round(inputs.outdoor_workers_pct, 2),
            norm_outdoor_workers=round(norm_workers, 4),
        )

    def compute_vulnerability_sub_index(self, inputs: VulnerabilityInputs) -> VulnerabilityBreakdown:
        """
        Computes normalized Vulnerability Sub-Index (V in [0.0, 1.0]).
        """
        norm_eld = min_max_scale(inputs.elderly_pct, self.bounds.elderly_min_pct, self.bounds.elderly_max_pct)
        norm_chi = min_max_scale(inputs.children_pct, self.bounds.children_min_pct, self.bounds.children_max_pct)
        norm_ac = min_max_scale(inputs.ac_deficit_pct, self.bounds.ac_deficit_min_pct, self.bounds.ac_deficit_max_pct)
        norm_chr = min_max_scale(
            inputs.chronic_conditions_pct,
            self.bounds.chronic_illness_min_pct,
            self.bounds.chronic_illness_max_pct,
        )
        norm_hou = min_max_scale(
            inputs.housing_uninsulated_pct,
            self.bounds.housing_vuln_min_pct,
            self.bounds.housing_vuln_max_pct,
        )

        sub_index = (
            self.vulnerability_weights.w_elderly * norm_eld
            + self.vulnerability_weights.w_children * norm_chi
            + self.vulnerability_weights.w_ac_deficit * norm_ac
            + self.vulnerability_weights.w_chronic_illness * norm_chr
            + self.vulnerability_weights.w_housing_vulnerability * norm_hou
        )
        sub_index = max(0.0, min(1.0, sub_index))

        return VulnerabilityBreakdown(
            sub_index=round(sub_index, 4),
            raw_elderly_pct=round(inputs.elderly_pct, 2),
            norm_elderly=round(norm_eld, 4),
            raw_children_pct=round(inputs.children_pct, 2),
            norm_children=round(norm_chi, 4),
            raw_ac_deficit_pct=round(inputs.ac_deficit_pct, 2),
            norm_ac_deficit=round(norm_ac, 4),
            raw_chronic_conditions_pct=round(inputs.chronic_conditions_pct, 2),
            norm_chronic_conditions=round(norm_chr, 4),
            raw_housing_uninsulated_pct=round(inputs.housing_uninsulated_pct, 2),
            norm_housing_uninsulated=round(norm_hou, 4),
        )

    # ------------------------------------------------------------------------
    # COMPOSITE HRI AGGREGATION & CATEGORIZATION
    # ------------------------------------------------------------------------

    def aggregate_hri(self, h: float, e: float, v: float) -> float:
        """
        Combines Hazard (H), Exposure (E), and Vulnerability (V) into
        Composite Heat Risk Index (HRI) scaled from 0.0 to 100.0.

        Mathematical formulations:
        - Geometric (Default IPCC AR6 multiplicative recommendation):
          HRI = 100 * (H * E * V)^(1/3)
          Zero-exposure or zero-hazard property: if E=0 or H=0, Risk=0.
        - Multiplicative-Scaled (Hazard gate with exposure-vulnerability interaction):
          HRI = 100 * H * sqrt(E * V)
        - Arithmetic (Multi-criteria additive proxy):
          HRI = 100 * (0.40*H + 0.30*E + 0.30*V)
        """
        h_c = max(0.0, min(1.0, h))
        e_c = max(0.0, min(1.0, e))
        v_c = max(0.0, min(1.0, v))

        if self.aggregation_mode == "geometric":
            score = 100.0 * math.pow(h_c * e_c * v_c, 1.0 / 3.0)
        elif self.aggregation_mode == "multiplicative_scaled":
            score = 100.0 * h_c * math.sqrt(e_c * v_c)
        elif self.aggregation_mode == "arithmetic":
            score = 100.0 * (0.40 * h_c + 0.30 * e_c + 0.30 * v_c)
        else:
            raise ValueError(f"Unknown aggregation mode: {self.aggregation_mode}")

        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def categorize_hri(hri_score: float) -> RiskCategory:
        """
        Categorizes composite HRI into defined bands:
        - Low: [0, 25]
        - Moderate: (25, 50]
        - High: (50, 70]
        - Severe: (70, 85]
        - Extreme: (85, 100]
        """
        if hri_score <= 25.0:
            return RiskCategory.LOW
        elif hri_score <= 50.0:
            return RiskCategory.MODERATE
        elif hri_score <= 70.0:
            return RiskCategory.HIGH
        elif hri_score <= 85.0:
            return RiskCategory.SEVERE
        else:
            return RiskCategory.EXTREME

    # ------------------------------------------------------------------------
    # THRESHOLD AUDIT & INTERVENTION DISCOVERY
    # ------------------------------------------------------------------------

    @staticmethod
    def identify_critical_flags_and_interventions(
        h_breakdown: HazardBreakdown,
        e_breakdown: ExposureBreakdown,
        v_breakdown: VulnerabilityBreakdown,
    ) -> Tuple[List[str], List[str]]:
        """
        Evaluates physical safety thresholds and generates targeted intervention recommendations.
        """
        flags: List[str] = []
        interventions: List[str] = []

        # 1. Physical Wet-Bulb physiological boundary check (31°C non-compensable, 35°C fatal)
        if h_breakdown.wet_bulb_c is not None:
            if h_breakdown.wet_bulb_c >= 35.0:
                flags.append("CRITICAL: 35°C Wet-Bulb Survivability Threshold Exceeded")
                interventions.append("Immediate mass evacuation to climate-controlled shelters.")
            elif h_breakdown.wet_bulb_c >= 31.0:
                flags.append("WARNING: Dangerous Wet-Bulb (>31°C) Physiological Limit Approaching")
                interventions.append("Halt all unconditioned outdoor physical activity.")

        # 2. Extreme Land Surface Temperature check (42°C+ extreme ground radiation)
        if h_breakdown.raw_lst_c >= 45.0:
            flags.append("CRITICAL: Severe Ground Thermal Radiation (LST >= 45°C)")
            interventions.append("Apply high-albedo cool pavement coatings; deploy emergency misting.")
        elif h_breakdown.raw_lst_c >= 42.0:
            flags.append("WARNING: Elevated Surface Urban Heat Island (LST >= 42°C)")
            interventions.append("Prioritize reflective surface treatments and street canyon shading.")

        # 3. High heat index
        if h_breakdown.raw_heat_index_c >= 42.0:
            flags.append("WARNING: NOAA Danger Category (Heat Index >= 42°C)")
            interventions.append("Distribute oral rehydration solutions (ORS) and establish hydration points.")

        # 4. Built-up density
        if h_breakdown.raw_ndbi >= 0.40:
            flags.append("HIGH_IMPERVIOUS_SURFACE: Severe Built-up Sensible Heat Retention")
            interventions.append("Implement pocket bioswales and green vegetative buffers.")

        # 5. Outdoor workers exposure
        if e_breakdown.raw_outdoor_workers_pct >= 20.0:
            flags.append("VULNERABLE_WORKFORCE: High Outdoor Labor Concentration (>= 20%)")
            interventions.append("Mandate 15-minute shaded rest breaks per hour and employer hydration supply.")

        # 6. High pedestrian foot-traffic
        if e_breakdown.raw_pedestrian_traffic >= 600.0:
            flags.append("HIGH_PEDESTRIAN_EXPOSURE: Densely Traversed Pedestrian Corridor")
            interventions.append("Erect tensile shade sails and rapid transit misting shelters.")

        # 7. Vulnerable demographics
        if v_breakdown.raw_elderly_pct >= 18.0 or v_breakdown.raw_children_pct >= 12.0:
            flags.append("DEMOGRAPHIC_VULNERABILITY: Elevated Elderly/Pediatric Heat Susceptibility")
            interventions.append("Direct outreach to nursing facilities, daycares, and local elder welfare.")

        # 8. AC deficit / Low income
        if v_breakdown.raw_ac_deficit_pct >= 60.0:
            flags.append("COOLING_POVERTY: High AC Deficit (>= 60% Unconditioned Households)")
            interventions.append("Open municipal buildings as 24/7 public cooling sanctuaries.")

        # 9. Informal housing / tin roofs
        if v_breakdown.raw_housing_uninsulated_pct >= 50.0:
            flags.append("HOUSING_HAZARD: Uninsulated / Metal Roof Concentration (>= 50%)")
            interventions.append("Subsidized cool roof elastomeric coating program for tin/sheet roofs.")

        # Fallback intervention if none generated
        if not interventions:
            interventions.append("Maintain urban tree health and routine seasonal hydration advisories.")

        return flags, interventions

    # ------------------------------------------------------------------------
    # WARD / GRID ZONE SCORER
    # ------------------------------------------------------------------------

    def score_ward(self, ward_input: WardRiskInput) -> HeatRiskScore:
        """
        Scores an administrative ward, census tract, or raster grid cell.
        """
        h_breakdown = self.compute_hazard_sub_index(ward_input.hazard)
        e_breakdown = self.compute_exposure_sub_index(ward_input.exposure)
        v_breakdown = self.compute_vulnerability_sub_index(ward_input.vulnerability)

        hri = self.aggregate_hri(
            h_breakdown.sub_index,
            e_breakdown.sub_index,
            v_breakdown.sub_index,
        )
        category = self.categorize_hri(hri)
        flags, interventions = self.identify_critical_flags_and_interventions(
            h_breakdown, e_breakdown, v_breakdown
        )

        return HeatRiskScore(
            entity_id=ward_input.ward_id,
            entity_name=ward_input.ward_name,
            entity_type="ward_grid",
            hri=hri,
            category=category,
            hazard_sub_index=h_breakdown.sub_index,
            exposure_sub_index=e_breakdown.sub_index,
            vulnerability_sub_index=v_breakdown.sub_index,
            hazard_breakdown=h_breakdown,
            exposure_breakdown=e_breakdown,
            vulnerability_breakdown=v_breakdown,
            critical_flags=flags,
            action_protocol=category.public_health_action,
            recommended_interventions=interventions,
            metadata={
                **ward_input.metadata,
                "area_sq_km": ward_input.area_sq_km,
            },
        )

    # ------------------------------------------------------------------------
    # STREET SEGMENT SCORER (HUMAN SCALE WITH MICROCLIMATE DOWNSCALING)
    # ------------------------------------------------------------------------

    def score_street_segment(self, street_input: StreetSegmentRiskInput) -> HeatRiskScore:
        """
        Scores a human-scale street segment incorporating microclimate features:
        - Tree canopy shade attenuation: reduces effective solar irradiance and surface LST.
        - Canyon aspect ratio: adjusts trapped sensible heat and microclimate ambient temperature.
        """
        canopy_fraction = max(0.0, min(1.0, street_input.tree_canopy_pct / 100.0))
        canyon_ratio = max(0.1, min(3.0, street_input.canyon_aspect_ratio))

        # 1. Microclimate attenuation of solar irradiance due to tree canopy
        # Unshaded solar radiation is attenuated by tree leaves (typical extinction factor ~75%)
        effective_solar = street_input.hazard.solar_irradiance_w_m2 * (1.0 - 0.75 * canopy_fraction)

        # 2. Localized LST microclimate dampening by tree canopy shade (empirical ~4.5°C per 100% canopy)
        effective_lst = street_input.hazard.lst_c - (4.5 * canopy_fraction)

        # 3. Canyon effect adjustment: Deep street canyons trap sensible heat nocturnal radiation,
        # slightly elevating microclimate air heat index (+0.8°C per unit aspect ratio > 1.0)
        canyon_excess = max(0.0, canyon_ratio - 1.0) * 0.8
        base_hi = street_input.hazard.resolve_heat_index()
        effective_hi = base_hi + canyon_excess - (1.5 * canopy_fraction)

        # Create localized microclimate hazard input
        street_hazard = HazardInputs(
            lst_c=effective_lst,
            heat_index_c=effective_hi,
            ndbi=street_input.hazard.ndbi,
            solar_irradiance_w_m2=effective_solar,
            air_temp_c=street_input.hazard.air_temp_c,
            relative_humidity=street_input.hazard.relative_humidity,
        )

        h_breakdown = self.compute_hazard_sub_index(street_hazard)
        e_breakdown = self.compute_exposure_sub_index(street_input.exposure)
        v_breakdown = self.compute_vulnerability_sub_index(street_input.vulnerability)

        hri = self.aggregate_hri(
            h_breakdown.sub_index,
            e_breakdown.sub_index,
            v_breakdown.sub_index,
        )
        category = self.categorize_hri(hri)
        flags, interventions = self.identify_critical_flags_and_interventions(
            h_breakdown, e_breakdown, v_breakdown
        )

        # Add street-specific physical insights
        if canopy_fraction < 0.15:
            flags.append("SHADE_DEFICIT: Low Street Tree Canopy (< 15%)")
            interventions.insert(0, "Plant high-leaf-area native shade trees along pedestrian paths.")
        if street_input.canyon_aspect_ratio > 1.5:
            flags.append("HEAT_TRAPPING_CANYON: Deep Street Canyon Aspect Ratio (> 1.5)")

        return HeatRiskScore(
            entity_id=street_input.segment_id,
            entity_name=street_input.street_name,
            entity_type="street_segment",
            hri=hri,
            category=category,
            hazard_sub_index=h_breakdown.sub_index,
            exposure_sub_index=e_breakdown.sub_index,
            vulnerability_sub_index=v_breakdown.sub_index,
            hazard_breakdown=h_breakdown,
            exposure_breakdown=e_breakdown,
            vulnerability_breakdown=v_breakdown,
            critical_flags=flags,
            action_protocol=category.public_health_action,
            recommended_interventions=interventions,
            metadata={
                **street_input.metadata,
                "length_meters": street_input.length_meters,
                "tree_canopy_pct": street_input.tree_canopy_pct,
                "canyon_aspect_ratio": street_input.canyon_aspect_ratio,
                "microclimate_lst_attenuation_c": round(street_input.hazard.lst_c - effective_lst, 2),
                "microclimate_solar_attenuation_w_m2": round(
                    street_input.hazard.solar_irradiance_w_m2 - effective_solar, 1
                ),
            },
        )

    # ------------------------------------------------------------------------
    # BATCH SCORING
    # ------------------------------------------------------------------------

    def batch_score_wards(self, wards: List[WardRiskInput]) -> List[HeatRiskScore]:
        """Scores a batch of wards/grid cells."""
        return [self.score_ward(w) for w in wards]

    def batch_score_street_segments(
        self, segments: List[StreetSegmentRiskInput]
    ) -> List[HeatRiskScore]:
        """Scores a batch of street segments."""
        return [self.score_street_segment(s) for s in segments]


# ============================================================================
# 7. INLINE SELF-TEST ASSERTIONS & VALIDATION SUITE
# ============================================================================

def _run_internal_validation() -> None:
    """Executes thorough production validation assertions for the risk engine."""
    print("--- Running Urban Heat Risk Engine Verification Suite ---")

    engine = UrbanHeatRiskEngine()

    # 1. Test biophysical calculations
    # Rothfusz heat index test: 35°C (95°F) with 60% RH should yield severe heat index (~45°C - 48°C)
    hi = calculate_heat_index(35.0, 60.0)
    assert 44.0 <= hi <= 49.0, f"Expected heat index between 44 and 49°C, got {hi}"

    # Stull wet bulb test: 35°C with 60% RH should yield ~28°C - 30°C
    tw = calculate_wet_bulb_temperature(35.0, 60.0)
    assert 27.0 <= tw <= 30.5, f"Expected wet bulb around 28-30°C, got {tw}"

    # 2. Extreme Danger Hazard Test: 45°C LST, 44°C Heat Index
    extreme_hazard = HazardInputs(
        lst_c=46.0,
        heat_index_c=45.0,
        ndbi=0.45,
        solar_irradiance_w_m2=950.0,
    )
    high_exposure = ExposureInputs(
        population_density_per_km2=22000.0,
        pedestrian_foot_traffic_hourly=800.0,
        outdoor_workers_pct=25.0,
    )
    high_vuln = VulnerabilityInputs(
        elderly_pct=22.0,
        children_pct=14.0,
        ac_deficit_pct=75.0,
        chronic_conditions_pct=28.0,
        housing_uninsulated_pct=65.0,
    )

    ward_extreme = WardRiskInput(
        ward_id="WARD_01_SLUM_CORE",
        ward_name="Central Dense Informal Ward",
        hazard=extreme_hazard,
        exposure=high_exposure,
        vulnerability=high_vuln,
        area_sq_km=2.4,
    )

    score_ext = engine.score_ward(ward_extreme)
    assert score_ext.hri >= 70.0, f"Expected severe/extreme HRI, got {score_ext.hri}"
    assert score_ext.category in [RiskCategory.SEVERE, RiskCategory.EXTREME]
    assert any("LST >= 45°C" in flag for flag in score_ext.critical_flags)
    assert any("COOLING_POVERTY" in flag for flag in score_ext.critical_flags)

    # 3. Low Risk / Vegetated Residential Test
    cool_hazard = HazardInputs(
        lst_c=26.0,
        heat_index_c=26.5,
        ndbi=-0.15,
        solar_irradiance_w_m2=350.0,
    )
    low_exposure = ExposureInputs(
        population_density_per_km2=1500.0,
        pedestrian_foot_traffic_hourly=30.0,
        outdoor_workers_pct=2.0,
    )
    low_vuln = VulnerabilityInputs(
        elderly_pct=10.0,
        children_pct=5.0,
        ac_deficit_pct=5.0,
        chronic_conditions_pct=8.0,
        housing_uninsulated_pct=2.0,
    )

    ward_cool = WardRiskInput(
        ward_id="WARD_02_GARDEN_SUBURB",
        ward_name="Green Garden Suburb",
        hazard=cool_hazard,
        exposure=low_exposure,
        vulnerability=low_vuln,
        area_sq_km=5.1,
    )

    score_cool = engine.score_ward(ward_cool)
    assert score_cool.hri <= 25.0, f"Expected Low HRI <= 25.0, got {score_cool.hri}"
    assert score_cool.category == RiskCategory.LOW

    # 4. Axiomatic Zero-Exposure Test (Uninhabited desert / industrial runway)
    zero_exposure = ExposureInputs(
        population_density_per_km2=0.0,
        pedestrian_foot_traffic_hourly=0.0,
        outdoor_workers_pct=0.0,
    )
    ward_uninhabited = WardRiskInput(
        ward_id="WARD_03_EMPTY_DESERT",
        ward_name="Uninhabited Solar Park",
        hazard=extreme_hazard,
        exposure=zero_exposure,
        vulnerability=high_vuln,
    )
    score_uninh = engine.score_ward(ward_uninhabited)
    assert score_uninh.hri == 0.0, f"Geometric IPCC formulation must yield 0 HRI for 0 exposure, got {score_uninh.hri}"

    # 5. Street Segment Microclimate Tree Canopy Test
    # Same base hazard, but compare 0% canopy vs 60% tree canopy
    street_exposed = StreetSegmentRiskInput(
        segment_id="STREET_01_UNSHADED",
        street_name="Grand Asphalt Avenue",
        hazard=extreme_hazard,
        exposure=high_exposure,
        vulnerability=high_vuln,
        length_meters=450.0,
        tree_canopy_pct=0.0,
        canyon_aspect_ratio=1.2,
    )
    street_shaded = StreetSegmentRiskInput(
        segment_id="STREET_02_CANOPY_BOULEVARD",
        street_name="Shaded Greenway Boulevard",
        hazard=extreme_hazard,
        exposure=high_exposure,
        vulnerability=high_vuln,
        length_meters=450.0,
        tree_canopy_pct=60.0,
        canyon_aspect_ratio=1.2,
    )

    score_street_exp = engine.score_street_segment(street_exposed)
    score_street_sha = engine.score_street_segment(street_shaded)

    # Shaded street must have significantly lower effective hazard and lower HRI
    assert score_street_sha.hri < score_street_exp.hri, (
        f"Tree canopy should reduce risk: shaded={score_street_sha.hri} vs exposed={score_street_exp.hri}"
    )
    assert score_street_sha.hazard_sub_index < score_street_exp.hazard_sub_index

    # 6. Test serialization
    score_dict = score_street_sha.to_dict()
    assert "hri" in score_dict
    assert "color_hex" in score_dict
    assert score_dict["entity_type"] == "street_segment"

    print("[SUCCESS] All 6 internal validation checks passed successfully!")


if __name__ == "__main__":
    _run_internal_validation()
