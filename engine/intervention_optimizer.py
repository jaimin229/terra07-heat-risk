"""
Urban Intervention & Resource Allocation Optimizer
Team TERRA07 - Software Track: Heat-Risk Mapping at Human Scale

This module provides:
1. Comprehensive catalog of heat mitigation interventions (costs, impacts, setup times).
2. Priority ranking by urgency (combining risk score, vulnerable population, and heat severity).
3. Budget-constrained knapsack optimization (maximizing lives protected and temperature reduction).
4. Rigorous ROI metrics (Lives Protected per $10k, Degrees Celsius reduction per dollar).
5. Simulated "What-If" post-intervention recalculation of microclimate temperatures and projected risk scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union


# ============================================================================
# 1. CATALOG OF HEAT MITIGATION INTERVENTIONS
# ============================================================================

class InterventionType(str, Enum):
    SHADE_SAILS = "shade_sails"
    MISTING_KIOSKS = "misting_kiosks"
    COOLING_CENTER = "cooling_center"
    URBAN_FORESTRY = "urban_forestry"
    COOL_ROOF = "cool_roof"


@dataclass(frozen=True)
class InterventionSpec:
    """Specification and characteristics of a heat mitigation intervention."""
    id: str
    name: str
    unit_cost: float
    unit_name: str
    temp_reduction_surface_c: float
    temp_reduction_ambient_c: float
    dehydration_heatstroke_reduction_pct: float
    setup_time_desc: str
    setup_hours: float
    capacity_people_per_unit: int
    best_for: str
    applicable_zone_types: tuple[str, ...]
    co_benefits: tuple[str, ...]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "unit_cost": self.unit_cost,
            "unit_name": self.unit_name,
            "temp_reduction_surface_c": self.temp_reduction_surface_c,
            "temp_reduction_ambient_c": self.temp_reduction_ambient_c,
            "dehydration_heatstroke_reduction_pct": self.dehydration_heatstroke_reduction_pct,
            "setup_time_desc": self.setup_time_desc,
            "setup_hours": self.setup_hours,
            "capacity_people_per_unit": self.capacity_people_per_unit,
            "best_for": self.best_for,
            "applicable_zone_types": list(self.applicable_zone_types),
            "co_benefits": list(self.co_benefits),
            "description": self.description,
        }


INTERVENTION_CATALOG: Dict[str, InterventionSpec] = {
    InterventionType.SHADE_SAILS.value: InterventionSpec(
        id=InterventionType.SHADE_SAILS.value,
        name="High-Albedo Shade Sails / Tensile Canopies",
        unit_cost=8000.0,
        unit_name="street",
        temp_reduction_surface_c=4.5,
        temp_reduction_ambient_c=1.8,
        dehydration_heatstroke_reduction_pct=35.0,
        setup_time_desc="Immediate 48h",
        setup_hours=48.0,
        capacity_people_per_unit=450,
        best_for="High foot-traffic vendor alleys",
        applicable_zone_types=(
            "vendor_market",
            "commercial_alley",
            "informal_settlement",
            "pedestrian_thoroughfare",
        ),
        co_benefits=(
            "Direct solar UV shielding",
            "Merchant economic continuity during heatwaves",
            "Rapid deployment with zero structural demolition",
        ),
        description=(
            "Tensioned high-albedo UV-reflective mesh fabrics installed over narrow streets "
            "and market alleys to block direct solar radiation and drastically lower ground surface heating."
        ),
    ),
    InterventionType.MISTING_KIOSKS.value: InterventionSpec(
        id=InterventionType.MISTING_KIOSKS.value,
        name="Solar-Powered Misting & Potable Hydration Kiosks",
        unit_cost=4500.0,
        unit_name="point",
        temp_reduction_surface_c=1.2,
        temp_reduction_ambient_c=2.5,
        dehydration_heatstroke_reduction_pct=65.0,
        setup_time_desc="72h",
        setup_hours=72.0,
        capacity_people_per_unit=600,
        best_for="Transit stops, outdoor labor hubs",
        applicable_zone_types=(
            "transit_hub",
            "outdoor_labor_hub",
            "bus_terminal",
            "vendor_market",
            "construction_corridor",
        ),
        co_benefits=(
            "Immediate physical core temperature lowering",
            "Free clean electrolyte hydration access",
            "Off-grid solar resilience during peak grid blackouts",
        ),
        description=(
            "Self-contained high-pressure micro-droplet misting stations paired with chilled "
            "potable water fountains powered by solar PV and battery buffers."
        ),
    ),
    InterventionType.COOLING_CENTER.value: InterventionSpec(
        id=InterventionType.COOLING_CENTER.value,
        name="Emergency AC Cooling Center Activation / Retrofit",
        unit_cost=25000.0,
        unit_name="center",
        temp_reduction_surface_c=0.0,
        temp_reduction_ambient_c=8.0,
        dehydration_heatstroke_reduction_pct=85.0,
        setup_time_desc="Immediate",
        setup_hours=24.0,
        capacity_people_per_unit=300,
        best_for="High elderly/informal housing wards",
        applicable_zone_types=(
            "informal_settlement",
            "dense_residential",
            "elderly_cluster",
            "low_income_ward",
        ),
        co_benefits=(
            "Life-saving climate controlled refuge for non-air-conditioned households",
            "Emergency medical checkups & rehydration salts distribution",
            "Backup generator resilience",
        ),
        description=(
            "Rapid activation and retrofit of community centers, municipal schools, or religious spaces "
            "with high-efficiency heat pumps, air scrubbers, cots, and medical triage."
        ),
    ),
    InterventionType.URBAN_FORESTRY.value: InterventionSpec(
        id=InterventionType.URBAN_FORESTRY.value,
        name="Urban Micro-Forestry & Street Tree Canopy Planting",
        unit_cost=12000.0,
        unit_name="km",
        temp_reduction_surface_c=7.0,
        temp_reduction_ambient_c=3.8,
        dehydration_heatstroke_reduction_pct=45.0,
        setup_time_desc="Seasonal",
        setup_hours=2160.0,  # ~90 days establishment
        capacity_people_per_unit=800,
        best_for="Wide unshaded avenues",
        applicable_zone_types=(
            "wide_avenue",
            "arterial_corridor",
            "boulevard",
            "residential_suburb",
            "riverfront_promenade",
        ),
        co_benefits=(
            "Permanent long-term evapotranspiration cooling",
            "Particulate air quality (PM2.5/PM10) filtration",
            "Stormwater runoff retention & biodiversity habitat",
        ),
        description=(
            "Dense native sapling planting along open road verges utilizing the Miyawaki micro-forest "
            "and continuous canopy technique with root guard and drip irrigation."
        ),
    ),
    InterventionType.COOL_ROOF.value: InterventionSpec(
        id=InterventionType.COOL_ROOF.value,
        name="Reflective Cool Roof Paint Subsidies",
        unit_cost=1200.0,
        unit_name="household",
        temp_reduction_surface_c=5.5,
        temp_reduction_ambient_c=3.5,  # Indoor Temp Reduction: -3.5°C
        dehydration_heatstroke_reduction_pct=50.0,
        setup_time_desc="Rapid (7 days)",
        setup_hours=168.0,
        capacity_people_per_unit=5,
        best_for="Dense tin-roof informal settlements",
        applicable_zone_types=(
            "informal_settlement",
            "tin_roof_slum",
            "dense_residential",
            "low_income_ward",
        ),
        co_benefits=(
            "Massive indoor living comfort improvement without AC electricity costs",
            "Reduction in heat-trapping thermal mass of sheet metal structures",
            "Community-level micro-albedo enhancement",
        ),
        description=(
            "Targeted subsidies and volunteer application of solar-reflective elastomeric acrylic "
            "cool coatings (SRI > 104) directly over galvanized iron and asbestos roofs."
        ),
    ),
}


# ============================================================================
# 2. URBAN ZONE & SPATIAL DATA MODELS
# ============================================================================

@dataclass
class UrbanZone:
    """Represents a municipal ward, census tract, or designated heat-risk zone."""
    zone_id: str
    name: str
    zone_type: str
    current_risk_score: float  # 0.0 to 100.0
    baseline_ambient_temp_c: float
    baseline_surface_temp_c: float
    total_population: int
    vulnerable_population: int
    area_sq_km: float

    # Environmental and structural attributes
    tin_roof_pct: float = 0.0  # 0 to 100
    canopy_cover_pct: float = 0.0  # 0 to 100
    elderly_pct: float = 0.0  # 0 to 100
    outdoor_labor_pct: float = 0.0  # 0 to 100
    foot_traffic_level: str = "Medium"  # Low, Medium, High, Extreme

    # Physical capacity caps for deployment in this zone
    max_shade_sails_streets: Optional[int] = None
    max_misting_kiosks: Optional[int] = None
    max_cooling_centers: Optional[int] = None
    max_forestry_km: Optional[float] = None
    max_cool_roof_households: Optional[int] = None

    # Optional spatial coordinates
    lat: Optional[float] = None
    lon: Optional[float] = None

    def __post_init__(self):
        # Validate ranges
        self.current_risk_score = max(0.0, min(100.0, float(self.current_risk_score)))
        self.total_population = max(1, int(self.total_population))
        self.vulnerable_population = max(0, min(self.total_population, int(self.vulnerable_population)))
        self.area_sq_km = max(0.01, float(self.area_sq_km))

        # Auto-compute realistic default capacity limits based on geography if unspecified
        if self.max_shade_sails_streets is None:
            # Narrow streets suitable for sails
            multiplier = 6 if self.foot_traffic_level in ("High", "Extreme") else 2
            self.max_shade_sails_streets = max(1, int(self.area_sq_km * multiplier))

        if self.max_misting_kiosks is None:
            # Transit & labor points
            transit_mult = 4 if self.zone_type in ("transit_hub", "outdoor_labor_hub", "vendor_market") else 2
            self.max_misting_kiosks = max(1, int(self.area_sq_km * transit_mult))

        if self.max_cooling_centers is None:
            # 1 center per 1,500 vulnerable people, min 1
            self.max_cooling_centers = max(1, min(10, math.ceil(self.vulnerable_population / 1500)))

        if self.max_forestry_km is None:
            # Kilometers of road verges eligible for planting
            self.max_forestry_km = round(max(0.2, self.area_sq_km * 2.5), 2)

        if self.max_cool_roof_households is None:
            # Estimated households with tin roofs
            avg_household_size = 4.5
            total_households = self.total_population / avg_household_size
            tin_households = int(total_households * (self.tin_roof_pct / 100.0))
            self.max_cool_roof_households = max(0, tin_households)

    def get_max_units(self, intervention_id: str) -> int:
        """Returns the maximum deployable units for an intervention in this zone."""
        if intervention_id == InterventionType.SHADE_SAILS.value:
            return self.max_shade_sails_streets or 0
        elif intervention_id == InterventionType.MISTING_KIOSKS.value:
            return self.max_misting_kiosks or 0
        elif intervention_id == InterventionType.COOLING_CENTER.value:
            return self.max_cooling_centers or 0
        elif intervention_id == InterventionType.URBAN_FORESTRY.value:
            return int(self.max_forestry_km or 0)
        elif intervention_id == InterventionType.COOL_ROOF.value:
            return self.max_cool_roof_households or 0
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 3. PRIORITY RANKING BY URGENCY
# ============================================================================

@dataclass
class RecommendedInterventionAdvice:
    """Action recommendation item for an urban zone."""
    intervention_id: str
    intervention_name: str
    unit_cost: float
    unit_name: str
    suitability_score: float  # 0.0 to 100.0
    projected_lives_protected_per_unit: int
    temp_reduction_desc: str
    setup_time_desc: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ZoneUrgencyRank:
    """Ranked zone output with urgency analytics and tailored intervention advice."""
    rank: int
    zone_id: str
    zone_name: str
    zone_type: str
    urgency_score: float  # 0.0 to 100.0
    current_risk_score: float
    vulnerable_headcount: int
    total_population: int
    vulnerability_density: float  # vulnerable persons / sq km
    baseline_ambient_temp_c: float
    baseline_surface_temp_c: float
    primary_risk_drivers: List[str]
    recommended_interventions: List[RecommendedInterventionAdvice]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "zone_type": self.zone_type,
            "urgency_score": round(self.urgency_score, 2),
            "current_risk_score": round(self.current_risk_score, 2),
            "vulnerable_headcount": self.vulnerable_headcount,
            "total_population": self.total_population,
            "vulnerability_density": round(self.vulnerability_density, 2),
            "baseline_ambient_temp_c": round(self.baseline_ambient_temp_c, 2),
            "baseline_surface_temp_c": round(self.baseline_surface_temp_c, 2),
            "primary_risk_drivers": self.primary_risk_drivers,
            "recommended_interventions": [rec.to_dict() for rec in self.recommended_interventions],
        }


# ============================================================================
# 4. OPTIMIZATION RESULT & ROI DATA STRUCTURES
# ============================================================================

@dataclass
class InterventionAllocation:
    """Allocated units of a specific intervention in a specific zone."""
    zone_id: str
    zone_name: str
    intervention_id: str
    intervention_name: str
    unit_count: int
    unit_name: str
    total_cost: float
    lives_protected: int
    ambient_temp_reduction_c: float
    surface_temp_reduction_c: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "intervention_id": self.intervention_id,
            "intervention_name": self.intervention_name,
            "unit_count": self.unit_count,
            "unit_name": self.unit_name,
            "total_cost": round(self.total_cost, 2),
            "lives_protected": self.lives_protected,
            "ambient_temp_reduction_c": round(self.ambient_temp_reduction_c, 2),
            "surface_temp_reduction_c": round(self.surface_temp_reduction_c, 2),
        }


@dataclass
class ZoneROIReport:
    """Detailed ROI summary for a single zone within an allocated portfolio."""
    zone_id: str
    zone_name: str
    allocated_budget: float
    allocated_units_by_type: Dict[str, int]
    lives_protected: int
    lives_protected_per_10k: float
    effective_temp_reduction_c: float
    celsius_reduction_per_dollar: float
    celsius_reduction_per_1000: float
    baseline_risk_score: float
    projected_risk_score: float
    risk_points_reduced: float
    risk_pct_reduced: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "allocated_budget": round(self.allocated_budget, 2),
            "allocated_units_by_type": self.allocated_units_by_type,
            "lives_protected": self.lives_protected,
            "lives_protected_per_10k": round(self.lives_protected_per_10k, 2),
            "effective_temp_reduction_c": round(self.effective_temp_reduction_c, 2),
            "celsius_reduction_per_dollar": f"{self.celsius_reduction_per_dollar:.7f}",
            "celsius_reduction_per_1000": round(self.celsius_reduction_per_1000, 4),
            "baseline_risk_score": round(self.baseline_risk_score, 2),
            "projected_risk_score": round(self.projected_risk_score, 2),
            "risk_points_reduced": round(self.risk_points_reduced, 2),
            "risk_pct_reduced": round(self.risk_pct_reduced, 2),
        }


@dataclass
class OptimizationResult:
    """Complete output of the budget-constrained knapsack optimization."""
    total_budget: float
    total_cost_spent: float
    remaining_budget: float
    budget_utilization_pct: float
    total_lives_protected: int
    total_effective_heat_reduction_deg_c: float
    average_risk_reduction_points: float

    # Core ROI Metrics
    lives_protected_per_10k_spent: float
    degrees_celsius_reduction_per_dollar: float
    degrees_celsius_reduction_per_1000_spent: float

    # Breakdown by intervention type across all zones
    spend_by_intervention: Dict[str, float]
    units_by_intervention: Dict[str, int]
    lives_protected_by_intervention: Dict[str, int]

    # Granular allocations and zone reports
    allocations: List[InterventionAllocation]
    zone_reports: List[ZoneROIReport]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_budget": round(self.total_budget, 2),
            "total_cost_spent": round(self.total_cost_spent, 2),
            "remaining_budget": round(self.remaining_budget, 2),
            "budget_utilization_pct": round(self.budget_utilization_pct, 2),
            "total_lives_protected": self.total_lives_protected,
            "total_effective_heat_reduction_deg_c": round(self.total_effective_heat_reduction_deg_c, 2),
            "average_risk_reduction_points": round(self.average_risk_reduction_points, 2),
            "roi": {
                "lives_protected_per_10k_spent": round(self.lives_protected_per_10k_spent, 2),
                "degrees_celsius_reduction_per_dollar": f"{self.degrees_celsius_reduction_per_dollar:.8f}",
                "degrees_celsius_reduction_per_1000_spent": round(self.degrees_celsius_reduction_per_1000_spent, 4),
            },
            "spend_by_intervention": {k: round(v, 2) for k, v in self.spend_by_intervention.items()},
            "units_by_intervention": self.units_by_intervention,
            "lives_protected_by_intervention": self.lives_protected_by_intervention,
            "allocations": [a.to_dict() for a in self.allocations],
            "zone_reports": [z.to_dict() for z in self.zone_reports],
            "metadata": self.metadata,
        }


# ============================================================================
# 5. WHAT-IF SIMULATION DATA MODELS
# ============================================================================

@dataclass
class WhatIfZoneResult:
    """Detailed microclimate and risk recalculation for a single zone after interventions."""
    zone_id: str
    zone_name: str
    baseline_risk_score: float
    projected_risk_score: float
    risk_score_reduction: float
    risk_reduction_pct: float

    # Microclimate temperature changes
    baseline_ambient_temp_c: float
    projected_ambient_temp_c: float
    ambient_temp_reduction_c: float

    baseline_surface_temp_c: float
    projected_surface_temp_c: float
    surface_temp_reduction_c: float

    # Impact headcounts
    vulnerable_headcount: int
    lives_protected: int
    unshielded_vulnerable_headcount: int
    vulnerable_protection_coverage_pct: float

    # Interventions deployed and financial summary
    deployed_interventions: Dict[str, int]
    total_cost: float
    fastest_relief_setup_desc: str
    risk_level_transition: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "baseline_risk_score": round(self.baseline_risk_score, 2),
            "projected_risk_score": round(self.projected_risk_score, 2),
            "risk_score_reduction": round(self.risk_score_reduction, 2),
            "risk_reduction_pct": round(self.risk_reduction_pct, 2),
            "temperatures": {
                "ambient": {
                    "baseline_c": round(self.baseline_ambient_temp_c, 2),
                    "projected_c": round(self.projected_ambient_temp_c, 2),
                    "reduction_c": round(self.ambient_temp_reduction_c, 2),
                },
                "surface": {
                    "baseline_c": round(self.baseline_surface_temp_c, 2),
                    "projected_c": round(self.projected_surface_temp_c, 2),
                    "reduction_c": round(self.surface_temp_reduction_c, 2),
                },
            },
            "vulnerability_impact": {
                "vulnerable_headcount": self.vulnerable_headcount,
                "lives_protected": self.lives_protected,
                "unshielded_vulnerable_headcount": self.unshielded_vulnerable_headcount,
                "coverage_pct": round(self.vulnerable_protection_coverage_pct, 2),
            },
            "deployed_interventions": self.deployed_interventions,
            "total_cost": round(self.total_cost, 2),
            "fastest_relief_setup_desc": self.fastest_relief_setup_desc,
            "risk_level_transition": self.risk_level_transition,
        }


@dataclass
class WhatIfPortfolioResult:
    """City-wide / multi-zone portfolio simulation result."""
    total_cost: float
    total_lives_protected: int
    average_baseline_risk: float
    average_projected_risk: float
    average_risk_reduction_points: float
    average_risk_reduction_pct: float
    max_zone_risk_reduction: float
    zones_evaluated_count: int
    zone_results: List[WhatIfZoneResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 2),
            "total_lives_protected": self.total_lives_protected,
            "average_baseline_risk": round(self.average_baseline_risk, 2),
            "average_projected_risk": round(self.average_projected_risk, 2),
            "average_risk_reduction_points": round(self.average_risk_reduction_points, 2),
            "average_risk_reduction_pct": round(self.average_risk_reduction_pct, 2),
            "max_zone_risk_reduction": round(self.max_zone_risk_reduction, 2),
            "zones_evaluated_count": self.zones_evaluated_count,
            "zone_results": [z.to_dict() for z in self.zone_results],
        }


# ============================================================================
# 6. OPTIMIZER & SIMULATION ENGINE
# ============================================================================

class InterventionOptimizer:
    """
    Core computational engine for Urban Intervention & Resource Allocation.

    Provides:
    - Priority Ranking by Urgency
    - Budget-Constrained Knapsack Optimization
    - Standardized ROI Evaluation
    - What-If Post-Intervention Recalculation
    """

    def __init__(self, catalog: Optional[Dict[str, InterventionSpec]] = None):
        self.catalog = catalog or INTERVENTION_CATALOG

    # ------------------------------------------------------------------------
    # ALGORITHM 1: Priority Ranking by Urgency
    # ------------------------------------------------------------------------
    def rank_zones_by_urgency(
        self,
        zones: List[UrbanZone],
        weight_risk: float = 0.35,
        weight_vulnerable_pop: float = 0.35,
        weight_heat_severity: float = 0.20,
        weight_density: float = 0.10,
    ) -> List[ZoneUrgencyRank]:
        """
        Calculates Urgency Score for each zone prioritizing areas with highest
        combined risk and vulnerable headcount, plus thermal hazard and density.
        Returns zones sorted in descending order of urgency.
        """
        if not zones:
            return []

        # Find maximum values for normalization
        max_vuln = max((z.vulnerable_population for z in zones), default=1)
        max_vuln = max(max_vuln, 1)

        densities = [z.vulnerable_population / max(0.01, z.area_sq_km) for z in zones]
        max_density = max(densities, default=1.0)
        max_density = max(max_density, 1.0)

        # Normalize weights to sum to 1.0
        total_w = weight_risk + weight_vulnerable_pop + weight_heat_severity + weight_density
        if total_w <= 0:
            total_w = 1.0
        w_r = weight_risk / total_w
        w_v = weight_vulnerable_pop / total_w
        w_h = weight_heat_severity / total_w
        w_d = weight_density / total_w

        ranked_items: List[ZoneUrgencyRank] = []

        for z in zones:
            # 1. Normalized Risk Factor (0.0 to 1.0)
            norm_risk = z.current_risk_score / 100.0

            # 2. Normalized Vulnerable Headcount (0.0 to 1.0)
            norm_vuln = z.vulnerable_population / max_vuln

            # 3. Heat Severity Index (ambient + surface deviation above human comfort thresholds)
            # 35°C ambient and 40°C surface are critical thresholds
            amb_excess = max(0.0, z.baseline_ambient_temp_c - 35.0) / 15.0  # scaled to ~50°C
            surf_excess = max(0.0, z.baseline_surface_temp_c - 40.0) / 20.0  # scaled to ~60°C
            heat_severity = min(1.0, (amb_excess * 0.5) + (surf_excess * 0.5))

            # 4. Vulnerable Density
            curr_density = z.vulnerable_population / max(0.01, z.area_sq_km)
            norm_density = min(1.0, curr_density / max_density)

            # Composite Urgency Score (0 to 100)
            urgency_score = (
                (w_r * norm_risk)
                + (w_v * norm_vuln)
                + (w_h * heat_severity)
                + (w_d * norm_density)
            ) * 100.0
            urgency_score = round(max(0.0, min(100.0, urgency_score)), 2)

            # Identify Primary Risk Drivers
            drivers: List[str] = []
            if z.current_risk_score >= 75.0:
                drivers.append(f"Critical baseline heat-risk score ({z.current_risk_score:.1f}/100)")
            elif z.current_risk_score >= 50.0:
                drivers.append(f"Elevated heat-risk score ({z.current_risk_score:.1f}/100)")

            if z.vulnerable_population >= 5000:
                drivers.append(f"Severe vulnerable population concentration ({z.vulnerable_population:,} residents)")
            elif z.vulnerable_population >= 2000:
                drivers.append(f"High vulnerable headcount ({z.vulnerable_population:,} residents)")

            if z.baseline_surface_temp_c >= 48.0:
                drivers.append(f"Extreme surface heat trap ({z.baseline_surface_temp_c:.1f}°C)")
            elif z.baseline_ambient_temp_c >= 42.0:
                drivers.append(f"Extreme ambient air temperature ({z.baseline_ambient_temp_c:.1f}°C)")

            if z.tin_roof_pct >= 40.0:
                drivers.append(f"High thermal emissivity tin-roof density ({z.tin_roof_pct:.0f}% of dwellings)")

            if curr_density >= 5000:
                drivers.append(f"High vulnerable density ({curr_density:,.0f} vulnerable/km²)")

            if not drivers:
                drivers.append("Standard heat-vulnerability profile")

            # Determine tailored intervention recommendations
            recommendations = self._evaluate_zone_interventions(z)

            ranked_items.append(
                ZoneUrgencyRank(
                    rank=0,  # Assigned after sorting
                    zone_id=z.zone_id,
                    zone_name=z.name,
                    zone_type=z.zone_type,
                    urgency_score=urgency_score,
                    current_risk_score=z.current_risk_score,
                    vulnerable_headcount=z.vulnerable_population,
                    total_population=z.total_population,
                    vulnerability_density=curr_density,
                    baseline_ambient_temp_c=z.baseline_ambient_temp_c,
                    baseline_surface_temp_c=z.baseline_surface_temp_c,
                    primary_risk_drivers=drivers,
                    recommended_interventions=recommendations,
                )
            )

        # Sort descending by urgency score (break ties with vulnerable headcount and risk)
        ranked_items.sort(
            key=lambda x: (x.urgency_score, x.vulnerable_headcount, x.current_risk_score),
            reverse=True,
        )

        # Assign 1-based ranks
        for idx, item in enumerate(ranked_items, start=1):
            item.rank = idx

        return ranked_items

    def _evaluate_zone_interventions(self, zone: UrbanZone) -> List[RecommendedInterventionAdvice]:
        """Calculates suitability and impact for each intervention given zone characteristics."""
        advice_list: List[RecommendedInterventionAdvice] = []

        for int_id, spec in self.catalog.items():
            suitability = 50.0  # Base suitability
            rationale_reasons = []

            # 1. Match zone type
            if zone.zone_type in spec.applicable_zone_types:
                suitability += 25.0
                rationale_reasons.append(f"Direct match for {zone.zone_type.replace('_', ' ')} environment")

            # 2. Specific environmental suitability boosts
            if int_id == InterventionType.COOL_ROOF.value:
                if zone.tin_roof_pct >= 40.0:
                    suitability += 25.0
                    rationale_reasons.append(f"Critical tin-roof coverage ({zone.tin_roof_pct:.0f}%) traps lethal indoor heat")
                elif zone.tin_roof_pct >= 15.0:
                    suitability += 15.0
                    rationale_reasons.append(f"Substantial tin-roof stock ({zone.tin_roof_pct:.0f}%)")
                else:
                    suitability -= 20.0

            elif int_id == InterventionType.SHADE_SAILS.value:
                if zone.foot_traffic_level in ("High", "Extreme"):
                    suitability += 20.0
                    rationale_reasons.append(f"{zone.foot_traffic_level} pedestrian foot-traffic needs immediate canopy shielding")
                if zone.zone_type == "vendor_market":
                    suitability += 15.0
                    rationale_reasons.append("Shields street merchants from direct ground thermal radiation")

            elif int_id == InterventionType.MISTING_KIOSKS.value:
                if zone.outdoor_labor_pct >= 25.0 or zone.zone_type in ("transit_hub", "outdoor_labor_hub"):
                    suitability += 25.0
                    rationale_reasons.append(f"High outdoor workforce exposure ({zone.outdoor_labor_pct:.0f}%) & transit density")
                if zone.baseline_ambient_temp_c >= 40.0:
                    suitability += 10.0
                    rationale_reasons.append(f"Severe ambient temperature ({zone.baseline_ambient_temp_c:.1f}°C) warrants rapid hydration/misting")

            elif int_id == InterventionType.COOLING_CENTER.value:
                if zone.elderly_pct >= 15.0:
                    suitability += 20.0
                    rationale_reasons.append(f"High elderly vulnerability ({zone.elderly_pct:.0f}%) requires climate-controlled indoor refuge")
                if zone.vulnerable_population >= 3000:
                    suitability += 15.0
                    rationale_reasons.append(f"Dense vulnerable population ({zone.vulnerable_population:,}) lacks AC infrastructure")

            elif int_id == InterventionType.URBAN_FORESTRY.value:
                if zone.canopy_cover_pct < 15.0:
                    suitability += 25.0
                    rationale_reasons.append(f"Deficient tree canopy ({zone.canopy_cover_pct:.1f}%) provides massive upside for micro-forestry")
                if zone.zone_type in ("wide_avenue", "arterial_corridor"):
                    suitability += 15.0
                    rationale_reasons.append("Ample street-verge space available for linear canopy planting")

            suitability = round(max(5.0, min(100.0, suitability)), 1)
            temp_desc = f"-{spec.temp_reduction_surface_c:.1f}°C surface, -{spec.temp_reduction_ambient_c:.1f}°C ambient"
            if int_id == InterventionType.COOL_ROOF.value:
                temp_desc = f"-{spec.temp_reduction_ambient_c:.1f}°C indoor, -{spec.temp_reduction_surface_c:.1f}°C roof surface"
            elif int_id == InterventionType.COOLING_CENTER.value:
                temp_desc = f"AC Indoor Refuge (8.0°C drop), Capacity: {spec.capacity_people_per_unit} people"

            rationale = "; ".join(rationale_reasons) if rationale_reasons else spec.best_for

            advice_list.append(
                RecommendedInterventionAdvice(
                    intervention_id=int_id,
                    intervention_name=spec.name,
                    unit_cost=spec.unit_cost,
                    unit_name=spec.unit_name,
                    suitability_score=suitability,
                    projected_lives_protected_per_unit=spec.capacity_people_per_unit,
                    temp_reduction_desc=temp_desc,
                    setup_time_desc=spec.setup_time_desc,
                    rationale=rationale,
                )
            )

        # Sort recommendations by suitability score
        advice_list.sort(key=lambda x: x.suitability_score, reverse=True)
        return advice_list

    # ------------------------------------------------------------------------
    # ALGORITHM 2: Budget-Constrained Knapsack Optimizer
    # ------------------------------------------------------------------------
    def optimize_budget(
        self,
        zones: List[UrbanZone],
        total_budget: float,
        objective: str = "balanced",
        min_urgency_percentile: float = 0.0,
        max_budget_per_zone_pct: Optional[float] = None,
        preferred_interventions: Optional[List[str]] = None,
    ) -> OptimizationResult:
        """
        Solves the budget-constrained multi-choice knapsack allocation problem.
        Maximizes composite impact (Lives Protected, Heat Reduction, and Urgency)
        subject to:
            sum(cost_i * units_i) <= total_budget
            units_i <= max_capacity_i for each zone
            lives_protected <= vulnerable_headcount for each zone (with diminishing returns)

        Objectives supported:
            - 'balanced': Weighted combination of lives protected, heat reduction, and urgency.
            - 'max_lives': Focuses primarily on maximizing vulnerable lives shielded.
            - 'max_heat_reduction': Focuses primarily on maximum area temperature cooling.
        """
        if total_budget <= 0 or not zones:
            return self._empty_optimization_result(total_budget)

        # Rank zones to obtain urgency baselines
        ranked_zones = self.rank_zones_by_urgency(zones)
        urgency_lookup = {r.zone_id: r.urgency_score for r in ranked_zones}
        zone_map = {z.zone_id: z for z in zones}

        # Filter zones if min_urgency_percentile is set
        if min_urgency_percentile > 0.0 and len(ranked_zones) > 1:
            threshold_idx = int(len(ranked_zones) * (1.0 - min_urgency_percentile))
            allowed_zone_ids = {r.zone_id for r in ranked_zones[: max(1, threshold_idx)]}
        else:
            allowed_zone_ids = set(zone_map.keys())

        # Precompute suitability map: (zone_id, int_id) -> float multiplier
        suitability_map: Dict[Tuple[str, str], float] = {}
        for r in ranked_zones:
            for rec in r.recommended_interventions:
                suitability_map[(r.zone_id, rec.intervention_id)] = max(0.2, rec.suitability_score / 50.0)

        # Build candidate allocation items
        # To handle diminishing marginal returns realistically, we discretize units or
        # evaluate the dynamic marginal utility of each incremental unit addition.
        allocated_units: Dict[Tuple[str, str], int] = {
            (z_id, int_id): 0
            for z_id in allowed_zone_ids
            for int_id in self.catalog.keys()
        }

        current_lives_protected: Dict[str, int] = {z_id: 0 for z_id in allowed_zone_ids}
        current_temp_reduction: Dict[str, float] = {z_id: 0.0 for z_id in allowed_zone_ids}
        zone_spend: Dict[str, float] = {z_id: 0.0 for z_id in allowed_zone_ids}

        remaining_budget = float(total_budget)
        max_zone_budget = (
            (total_budget * (max_budget_per_zone_pct / 100.0))
            if max_budget_per_zone_pct is not None
            else float("inf")
        )

        catalog_keys = [
            k for k in self.catalog.keys()
            if preferred_interventions is None or k in preferred_interventions
        ]

        # Greedy Marginal Utility with dynamic state updates
        # This solves bounded multi-choice knapsack with concave diminishing returns in O(N * (Budget/min_cost))
        while remaining_budget >= min(spec.unit_cost for spec in self.catalog.values()):
            best_choice: Optional[Tuple[str, str]] = None
            best_marginal_utility_per_dollar: float = -1.0

            for z_id in allowed_zone_ids:
                z = zone_map[z_id]
                u_score = urgency_lookup.get(z_id, 50.0)

                # Check zone budget limit
                if zone_spend[z_id] >= max_zone_budget:
                    continue

                for int_id in catalog_keys:
                    spec = self.catalog[int_id]
                    unit_cost = spec.unit_cost

                    if unit_cost > remaining_budget:
                        continue
                    if (zone_spend[z_id] + unit_cost) > max_zone_budget:
                        continue

                    # Check zone physical capacity limit
                    current_count = allocated_units[(z_id, int_id)]
                    max_cap = z.get_max_units(int_id)
                    if current_count >= max_cap:
                        continue

                    # Calculate marginal gain for adding 1 more unit of this intervention
                    # 1. Marginal Lives Protected
                    already_shielded = current_lives_protected[z_id]
                    remaining_vuln = max(0, z.vulnerable_population - already_shielded)

                    # Base capacity of unit
                    raw_capacity = spec.capacity_people_per_unit

                    # If informal settlement and cool roof, boost lives directly shielded indoor
                    if int_id == InterventionType.COOL_ROOF.value:
                        effective_add = min(raw_capacity, remaining_vuln)
                    elif int_id == InterventionType.COOLING_CENTER.value:
                        effective_add = min(raw_capacity, remaining_vuln)
                    elif int_id == InterventionType.MISTING_KIOSKS.value:
                        # Outdoor labor / transit throughput
                        factor = 1.2 if z.outdoor_labor_pct > 20.0 or z.zone_type == "transit_hub" else 0.8
                        effective_add = min(int(raw_capacity * factor), remaining_vuln)
                    elif int_id == InterventionType.SHADE_SAILS.value:
                        factor = 1.3 if z.foot_traffic_level in ("High", "Extreme") else 0.7
                        effective_add = min(int(raw_capacity * factor), remaining_vuln)
                    else:  # Urban forestry
                        effective_add = min(raw_capacity, remaining_vuln)

                    # Diminishing returns factor as zone coverage approaches 100%
                    coverage_ratio = already_shielded / max(1, z.vulnerable_population)
                    diminishing_mult = max(0.2, 1.0 - (coverage_ratio * 0.75))
                    marginal_lives = effective_add * diminishing_mult

                    # 2. Marginal Temperature Reduction
                    curr_t = current_temp_reduction[z_id]
                    # Asymptotic cooling cap: microclimates cannot cool by more than 8°C total
                    max_cooling_cap = 8.0
                    room_for_cooling = max(0.0, max_cooling_cap - curr_t)
                    unit_raw_cooling = (0.6 * spec.temp_reduction_ambient_c) + (0.4 * spec.temp_reduction_surface_c)
                    marginal_temp = min(unit_raw_cooling * (room_for_cooling / max_cooling_cap), room_for_cooling)

                    # 3. Objective Scoring
                    suit_mult = suitability_map.get((z_id, int_id), 1.0)
                    urgency_mult = 1.0 + (u_score / 50.0)

                    # Spatial footprint weight of cooling (distinguishing household vs avenue vs street)
                    spatial_footprint = {
                        InterventionType.URBAN_FORESTRY.value: 2.5,
                        InterventionType.SHADE_SAILS.value: 1.2,
                        InterventionType.MISTING_KIOSKS.value: 0.8,
                        InterventionType.COOL_ROOF.value: 0.3,
                        InterventionType.COOLING_CENTER.value: 0.2,
                    }.get(int_id, 1.0)

                    if objective == "max_lives":
                        score = (marginal_lives * suit_mult) * urgency_mult
                    elif objective == "max_heat_reduction":
                        score = (marginal_temp * spatial_footprint * 80.0 * suit_mult) * urgency_mult
                    else:  # 'balanced' default
                        # Synergistic blend of lives shielded and microclimate cooling
                        score = (
                            (marginal_lives * 1.0)
                            + (marginal_temp * spatial_footprint * 60.0)
                        ) * suit_mult * urgency_mult

                    utility_per_dollar = score / unit_cost

                    if utility_per_dollar > best_marginal_utility_per_dollar:
                        best_marginal_utility_per_dollar = utility_per_dollar
                        best_choice = (z_id, int_id)

            if best_choice is None or best_marginal_utility_per_dollar <= 0:
                # No eligible candidate fits within budget or capacity
                break

            # Commit the best choice
            c_zid, c_intid = best_choice
            c_spec = self.catalog[c_intid]
            c_zone = zone_map[c_zid]

            allocated_units[(c_zid, c_intid)] += 1
            zone_spend[c_zid] += c_spec.unit_cost
            remaining_budget -= c_spec.unit_cost

            # Update state
            # Update shielded headcount
            raw_cap = c_spec.capacity_people_per_unit
            rem_v = max(0, c_zone.vulnerable_population - current_lives_protected[c_zid])
            gain = min(raw_cap, rem_v)
            current_lives_protected[c_zid] += int(gain)

            # Update cooling
            unit_eff_t = (0.6 * c_spec.temp_reduction_ambient_c) + (0.4 * c_spec.temp_reduction_surface_c)
            current_temp_reduction[c_zid] = min(8.0, current_temp_reduction[c_zid] + (unit_eff_t * 0.35))

        # Build detailed allocation and ROI outputs
        allocations_list: List[InterventionAllocation] = []
        spend_by_intervention: Dict[str, float] = {k: 0.0 for k in self.catalog.keys()}
        units_by_intervention: Dict[str, int] = {k: 0 for k in self.catalog.keys()}
        lives_by_intervention: Dict[str, int] = {k: 0 for k in self.catalog.keys()}

        total_spent = float(total_budget - remaining_budget)
        total_lives = 0
        total_deg_c = 0.0

        for (z_id, int_id), count in allocated_units.items():
            if count <= 0:
                continue
            z = zone_map[z_id]
            spec = self.catalog[int_id]
            cost = count * spec.unit_cost
            # Direct unit impact
            int_lives = min(z.vulnerable_population, count * spec.capacity_people_per_unit)
            amb_t = min(5.0, count * spec.temp_reduction_ambient_c * 0.4)
            surf_t = min(9.0, count * spec.temp_reduction_surface_c * 0.4)

            allocations_list.append(
                InterventionAllocation(
                    zone_id=z_id,
                    zone_name=z.name,
                    intervention_id=int_id,
                    intervention_name=spec.name,
                    unit_count=count,
                    unit_name=spec.unit_name,
                    total_cost=cost,
                    lives_protected=int_lives,
                    ambient_temp_reduction_c=amb_t,
                    surface_temp_reduction_c=surf_t,
                )
            )

            spend_by_intervention[int_id] += cost
            units_by_intervention[int_id] += count
            lives_by_intervention[int_id] += int_lives

        # Compute Zone-level ROI and What-If analytics
        zone_reports: List[ZoneROIReport] = []
        risk_reductions_total = 0.0

        for z in zones:
            z_id = z.zone_id
            z_cost = zone_spend.get(z_id, 0.0)
            z_units = {
                int_id: allocated_units.get((z_id, int_id), 0)
                for int_id in self.catalog.keys()
                if allocated_units.get((z_id, int_id), 0) > 0
            }

            # Run What-If simulation for this zone
            sim = self.simulate_what_if(z, z_units)

            z_lives = sim.lives_protected
            eff_t = (0.6 * sim.ambient_temp_reduction_c) + (0.4 * sim.surface_temp_reduction_c)

            total_lives += z_lives
            total_deg_c += eff_t
            risk_reductions_total += sim.risk_score_reduction

            # Lives per $10k spent in this zone
            z_lives_per_10k = (z_lives / z_cost * 10000.0) if z_cost > 0 else 0.0
            # Degrees Celsius reduction per dollar in this zone
            z_c_per_dollar = (eff_t / z_cost) if z_cost > 0 else 0.0
            z_c_per_1000 = z_c_per_dollar * 1000.0

            if z_cost > 0 or len(zones) <= 10:
                zone_reports.append(
                    ZoneROIReport(
                        zone_id=z_id,
                        zone_name=z.name,
                        allocated_budget=z_cost,
                        allocated_units_by_type=z_units,
                        lives_protected=z_lives,
                        lives_protected_per_10k=round(z_lives_per_10k, 2),
                        effective_temp_reduction_c=round(eff_t, 2),
                        celsius_reduction_per_dollar=z_c_per_dollar,
                        celsius_reduction_per_1000=round(z_c_per_1000, 4),
                        baseline_risk_score=z.current_risk_score,
                        projected_risk_score=sim.projected_risk_score,
                        risk_points_reduced=sim.risk_score_reduction,
                        risk_pct_reduced=sim.risk_reduction_pct,
                    )
                )

        # Portfolio-level ROI metrics
        utilization_pct = (total_spent / total_budget * 100.0) if total_budget > 0 else 0.0
        portfolio_lives_per_10k = (total_lives / total_spent * 10000.0) if total_spent > 0 else 0.0
        reported_total_deg_c = round(total_deg_c, 2)
        portfolio_celsius_per_dollar = (reported_total_deg_c / total_spent) if total_spent > 0 else 0.0
        portfolio_celsius_per_1000 = portfolio_celsius_per_dollar * 1000.0
        avg_risk_reduction = (risk_reductions_total / len(zones)) if zones else 0.0

        # Sort allocations by total cost descending
        allocations_list.sort(key=lambda a: a.total_cost, reverse=True)
        # Sort zone reports by budget spent descending
        zone_reports.sort(key=lambda zr: zr.allocated_budget, reverse=True)

        return OptimizationResult(
            total_budget=round(total_budget, 2),
            total_cost_spent=round(total_spent, 2),
            remaining_budget=round(remaining_budget, 2),
            budget_utilization_pct=round(utilization_pct, 2),
            total_lives_protected=total_lives,
            total_effective_heat_reduction_deg_c=round(total_deg_c, 2),
            average_risk_reduction_points=round(avg_risk_reduction, 2),
            lives_protected_per_10k_spent=round(portfolio_lives_per_10k, 2),
            degrees_celsius_reduction_per_dollar=portfolio_celsius_per_dollar,
            degrees_celsius_reduction_per_1000_spent=round(portfolio_celsius_per_1000, 4),
            spend_by_intervention=spend_by_intervention,
            units_by_intervention=units_by_intervention,
            lives_protected_by_intervention=lives_by_intervention,
            allocations=allocations_list,
            zone_reports=zone_reports,
            metadata={
                "objective": objective,
                "zones_allocated_count": sum(1 for zr in zone_reports if zr.allocated_budget > 0),
                "total_zones_considered": len(zones),
            },
        )

    def _empty_optimization_result(self, total_budget: float) -> OptimizationResult:
        """Returns zero-allocation result for invalid or zero budget."""
        return OptimizationResult(
            total_budget=round(max(0.0, total_budget), 2),
            total_cost_spent=0.0,
            remaining_budget=round(max(0.0, total_budget), 2),
            budget_utilization_pct=0.0,
            total_lives_protected=0,
            total_effective_heat_reduction_deg_c=0.0,
            average_risk_reduction_points=0.0,
            lives_protected_per_10k_spent=0.0,
            degrees_celsius_reduction_per_dollar=0.0,
            degrees_celsius_reduction_per_1000_spent=0.0,
            spend_by_intervention={k: 0.0 for k in self.catalog.keys()},
            units_by_intervention={k: 0 for k in self.catalog.keys()},
            lives_protected_by_intervention={k: 0 for k in self.catalog.keys()},
            allocations=[],
            zone_reports=[],
            metadata={"status": "No allocation made (zero budget or empty zones)"},
        )

    # ------------------------------------------------------------------------
    # ALGORITHM 3 & 4: What-If Post-Intervention Recalculation Engine
    # ------------------------------------------------------------------------
    def simulate_what_if(
        self,
        zone: UrbanZone,
        deployed_interventions: Dict[str, int],
    ) -> WhatIfZoneResult:
        """
        Simulates the post-intervention microclimate state and projected Risk Score
        after a bundle of heat interventions is deployed in an urban zone.

        Models:
        - Physics-based ambient and surface temperature reduction with diminishing returns.
        - Direct morbidity and dehydration/heatstroke shielding of vulnerable headcount.
        - Standard IPCC Heat Risk Framework: Risk = Hazard * Exposure * Vulnerability.
        """
        clean_deployed = {
            k: max(0, int(v))
            for k, v in deployed_interventions.items()
            if max(0, int(v)) > 0 and k in self.catalog
        }

        if not clean_deployed:
            # Baseline unchanged
            risk_cat = self._get_risk_category(zone.current_risk_score)
            return WhatIfZoneResult(
                zone_id=zone.zone_id,
                zone_name=zone.name,
                baseline_risk_score=zone.current_risk_score,
                projected_risk_score=zone.current_risk_score,
                risk_score_reduction=0.0,
                risk_reduction_pct=0.0,
                baseline_ambient_temp_c=zone.baseline_ambient_temp_c,
                projected_ambient_temp_c=zone.baseline_ambient_temp_c,
                ambient_temp_reduction_c=0.0,
                baseline_surface_temp_c=zone.baseline_surface_temp_c,
                projected_surface_temp_c=zone.baseline_surface_temp_c,
                surface_temp_reduction_c=0.0,
                vulnerable_headcount=zone.vulnerable_population,
                lives_protected=0,
                unshielded_vulnerable_headcount=zone.vulnerable_population,
                vulnerable_protection_coverage_pct=0.0,
                deployed_interventions={},
                total_cost=0.0,
                fastest_relief_setup_desc="None deployed",
                risk_level_transition=f"{risk_cat} ({zone.current_risk_score:.1f}) -> Unchanged",
            )

        # 1. Calculate cumulative physical thermal reduction
        # Using asymptotic saturation curves to prevent unphysical drops
        # Ambient temperature saturation limit: ~6.5°C drop max outdoors
        # Surface temperature saturation limit: ~12.0°C drop max
        raw_ambient_delta = 0.0
        raw_surface_delta = 0.0
        total_cost = 0.0
        total_capacity_people = 0
        min_setup_hours = float("inf")
        fastest_setup_desc = "Immediate"

        for int_id, count in clean_deployed.items():
            spec = self.catalog[int_id]
            total_cost += count * spec.unit_cost

            # Track fastest deployment setup time
            if spec.setup_hours < min_setup_hours:
                min_setup_hours = spec.setup_hours
                fastest_setup_desc = spec.setup_time_desc

            # Scale raw thermal contributions
            if int_id == InterventionType.COOL_ROOF.value:
                # Cool roof heavily drops surface and indoor ambient
                # Normalize count by total households in zone
                tin_coverage = min(1.0, count / max(1, zone.max_cool_roof_households or 100))
                raw_surface_delta += spec.temp_reduction_surface_c * (tin_coverage ** 0.7)
                raw_ambient_delta += spec.temp_reduction_ambient_c * (tin_coverage ** 0.8)
                total_capacity_people += count * spec.capacity_people_per_unit

            elif int_id == InterventionType.SHADE_SAILS.value:
                # Shade sails block direct solar irradiance on streets
                street_coverage = min(1.0, count / max(1, zone.max_shade_sails_streets or 5))
                raw_surface_delta += spec.temp_reduction_surface_c * (street_coverage ** 0.75)
                raw_ambient_delta += spec.temp_reduction_ambient_c * (street_coverage ** 0.8)
                total_capacity_people += count * spec.capacity_people_per_unit

            elif int_id == InterventionType.MISTING_KIOSKS.value:
                # Localized evaporative cooling & vital hydration
                kiosk_coverage = min(1.0, count / max(1, zone.max_misting_kiosks or 4))
                raw_ambient_delta += spec.temp_reduction_ambient_c * (kiosk_coverage ** 0.6)
                raw_surface_delta += spec.temp_reduction_surface_c * (kiosk_coverage ** 0.6)
                total_capacity_people += count * spec.capacity_people_per_unit

            elif int_id == InterventionType.COOLING_CENTER.value:
                # Indoor refrigerated sanctuary
                total_capacity_people += count * spec.capacity_people_per_unit
                # Local area ambient benefit is minor, but indoor safety is huge
                raw_ambient_delta += 0.3 * count

            elif int_id == InterventionType.URBAN_FORESTRY.value:
                # Evapotranspiration canopy
                km_coverage = min(1.0, count / max(0.5, zone.max_forestry_km or 2.0))
                raw_ambient_delta += spec.temp_reduction_ambient_c * (km_coverage ** 0.7)
                raw_surface_delta += spec.temp_reduction_surface_c * (km_coverage ** 0.7)
                total_capacity_people += count * spec.capacity_people_per_unit

        # Apply diminishing returns saturation function: T_drop = T_max * (1 - exp(-raw / T_max))
        ambient_max_drop = 6.5
        surface_max_drop = 12.0

        ambient_reduction = ambient_max_drop * (1.0 - math.exp(-raw_ambient_delta / ambient_max_drop))
        surface_reduction = surface_max_drop * (1.0 - math.exp(-raw_surface_delta / surface_max_drop))

        ambient_reduction = round(max(0.0, ambient_reduction), 2)
        surface_reduction = round(max(0.0, surface_reduction), 2)

        projected_ambient = round(zone.baseline_ambient_temp_c - ambient_reduction, 2)
        projected_surface = round(zone.baseline_surface_temp_c - surface_reduction, 2)

        # 2. Vulnerable Lives Shielded
        effective_lives_protected = min(zone.vulnerable_population, int(total_capacity_people))
        unshielded = max(0, zone.vulnerable_population - effective_lives_protected)
        coverage_pct = (
            (effective_lives_protected / zone.vulnerable_population * 100.0)
            if zone.vulnerable_population > 0
            else 100.0
        )

        # 3. Projected Risk Score Recalculation
        # In IPCC heat risk: Risk = Hazard * Exposure * Vulnerability
        # Hazard Factor: reduction in thermal excess
        baseline_excess = max(1.0, zone.baseline_ambient_temp_c - 28.0)  # thermal comfort base
        post_excess = max(1.0, projected_ambient - 28.0)
        hazard_ratio = post_excess / baseline_excess

        # Vulnerability Factor: reduction in vulnerable fraction lacking cooling or hydration
        shielded_ratio = effective_lives_protected / max(1, zone.vulnerable_population)
        vulnerability_retention = 1.0 - (shielded_ratio * 0.65)  # up to 65% physiological vulnerability drop

        # Surface heat factor (reduces radiant heat stroke load)
        surf_retention = 1.0 - (min(surface_reduction, 8.0) / 30.0)

        # Combined post-intervention risk multiplier
        risk_multiplier = (0.45 * hazard_ratio) + (0.40 * vulnerability_retention) + (0.15 * surf_retention)
        risk_multiplier = max(0.15, min(1.0, risk_multiplier))

        projected_risk = round(zone.current_risk_score * risk_multiplier, 2)
        risk_points_dropped = round(zone.current_risk_score - projected_risk, 2)
        risk_reduction_pct = (
            round((risk_points_dropped / zone.current_risk_score) * 100.0, 2)
            if zone.current_risk_score > 0
            else 0.0
        )

        old_cat = self._get_risk_category(zone.current_risk_score)
        new_cat = self._get_risk_category(projected_risk)
        transition = f"{old_cat} ({zone.current_risk_score:.1f}) -> {new_cat} ({projected_risk:.1f})"

        return WhatIfZoneResult(
            zone_id=zone.zone_id,
            zone_name=zone.name,
            baseline_risk_score=zone.current_risk_score,
            projected_risk_score=projected_risk,
            risk_score_reduction=risk_points_dropped,
            risk_reduction_pct=risk_reduction_pct,
            baseline_ambient_temp_c=zone.baseline_ambient_temp_c,
            projected_ambient_temp_c=projected_ambient,
            ambient_temp_reduction_c=ambient_reduction,
            baseline_surface_temp_c=zone.baseline_surface_temp_c,
            projected_surface_temp_c=projected_surface,
            surface_temp_reduction_c=surface_reduction,
            vulnerable_headcount=zone.vulnerable_population,
            lives_protected=effective_lives_protected,
            unshielded_vulnerable_headcount=unshielded,
            vulnerable_protection_coverage_pct=round(coverage_pct, 2),
            deployed_interventions=clean_deployed,
            total_cost=round(total_cost, 2),
            fastest_relief_setup_desc=fastest_setup_desc,
            risk_level_transition=transition,
        )

    def simulate_portfolio_what_if(
        self,
        zones: List[UrbanZone],
        portfolio_deployments: Dict[str, Dict[str, int]],
    ) -> WhatIfPortfolioResult:
        """
        Simulates city-wide impact across multiple zones given a deployment mapping:
        portfolio_deployments: { zone_id: { intervention_id: unit_count } }
        """
        zone_map = {z.zone_id: z for z in zones}
        results: List[WhatIfZoneResult] = []
        total_cost = 0.0
        total_lives = 0

        # Handle OptimizationResult instance or dict
        if hasattr(portfolio_deployments, "allocations"):
            deploy_dict: Dict[str, Dict[str, int]] = {}
            for alloc in portfolio_deployments.allocations:
                deploy_dict.setdefault(alloc.zone_id, {})[alloc.intervention_id] = alloc.unit_count
            portfolio_deployments = deploy_dict

        baseline_risks = []
        projected_risks = []

        for z in zones:
            z_dep = portfolio_deployments.get(z.zone_id, {})
            sim = self.simulate_what_if(z, z_dep)
            results.append(sim)
            total_cost += sim.total_cost
            total_lives += sim.lives_protected
            baseline_risks.append(sim.baseline_risk_score)
            projected_risks.append(sim.projected_risk_score)

        avg_base = (sum(baseline_risks) / len(zones)) if zones else 0.0
        avg_proj = (sum(projected_risks) / len(zones)) if zones else 0.0
        avg_drop = avg_base - avg_proj
        avg_drop_pct = (avg_drop / avg_base * 100.0) if avg_base > 0 else 0.0
        max_drop = max((r.risk_score_reduction for r in results), default=0.0)

        return WhatIfPortfolioResult(
            total_cost=round(total_cost, 2),
            total_lives_protected=total_lives,
            average_baseline_risk=round(avg_base, 2),
            average_projected_risk=round(avg_proj, 2),
            average_risk_reduction_points=round(avg_drop, 2),
            average_risk_reduction_pct=round(avg_drop_pct, 2),
            max_zone_risk_reduction=round(max_drop, 2),
            zones_evaluated_count=len(zones),
            zone_results=results,
        )

    # ------------------------------------------------------------------------
    # SCENARIO COMPARISON & UTILITIES
    # ------------------------------------------------------------------------
    def compare_budget_scenarios(
        self,
        zones: List[UrbanZone],
        budgets: List[float],
        objective: str = "balanced",
    ) -> Dict[str, Any]:
        """
        Compares multiple investment budget tiers (e.g. $50k, $100k, $250k, $500k, $1M)
        to evaluate the investment-impact frontier.
        """
        scenarios = []
        for b in sorted(budgets):
            res = self.optimize_budget(zones, total_budget=b, objective=objective)
            scenarios.append({
                "budget": round(b, 2),
                "cost_spent": res.total_cost_spent,
                "budget_utilization_pct": res.budget_utilization_pct,
                "lives_protected": res.total_lives_protected,
                "lives_protected_per_10k": res.lives_protected_per_10k_spent,
                "effective_heat_reduction_deg_c": res.total_effective_heat_reduction_deg_c,
                "celsius_reduction_per_1000": res.degrees_celsius_reduction_per_1000_spent,
                "average_risk_reduction_points": res.average_risk_reduction_points,
                "units_by_type": res.units_by_intervention,
            })

        return {
            "objective": objective,
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
        }

    def generate_executive_summary(
        self,
        optimization_result: OptimizationResult,
        ranked_zones: List[ZoneUrgencyRank],
    ) -> str:
        """Generates an executive markdown briefing for municipal leaders & city planners."""
        res = optimization_result
        top_zone = ranked_zones[0] if ranked_zones else None

        summary = [
            f"# TERRA07 Heat Mitigation Resource Allocation Briefing",
            f"**Total Authorized Budget:** ${res.total_budget:,.2f} | **Deployed Investment:** ${res.total_cost_spent:,.2f} ({res.budget_utilization_pct:.1f}% utilized)",
            f"",
            f"## Key Impact Metrics",
            f"- **Vulnerable Lives Protected:** {res.total_lives_protected:,} residents",
            f"- **Cumulative Area Cooling:** {res.total_effective_heat_reduction_deg_c:.2f}°C",
            f"- **Average Risk Reduction:** -{res.average_risk_reduction_points:.2f} risk score points",
            f"- **Capital Efficiency (ROI):** **{res.lives_protected_per_10k_spent:.1f} lives protected per $10,000 invested**",
            f"- **Thermal ROI:** **{res.degrees_celsius_reduction_per_1000_spent:.4f}°C cooling per $1,000 spent** (${1.0 / res.degrees_celsius_reduction_per_dollar:,.2f} per 1.0°C drop)" if res.degrees_celsius_reduction_per_dollar > 0 else "",
            f"",
            f"## Highest Priority Urgency Ward",
        ]

        if top_zone:
            summary.extend([
                f"- **Ward Name:** {top_zone.zone_name} (`{top_zone.zone_id}`)",
                f"- **Urgency Score:** {top_zone.urgency_score:.1f}/100 (Risk: {top_zone.current_risk_score:.1f}, Vulnerable Headcount: {top_zone.vulnerable_headcount:,})",
                f"- **Primary Hazard Drivers:** {', '.join(top_zone.primary_risk_drivers)}",
            ])

        summary.extend([
            f"",
            f"## Resource Deployment Breakdown by Intervention",
            f"| Intervention | Units Deployed | Capital Spent | Lives Shielded |",
            f"| :--- | :--- | :--- | :--- |",
        ])

        for int_id, count in res.units_by_intervention.items():
            spec = self.catalog[int_id]
            spent = res.spend_by_intervention[int_id]
            lives = res.lives_protected_by_intervention[int_id]
            summary.append(
                f"| {spec.name} | {count} {spec.unit_name}s | ${spent:,.2f} | {lives:,} |"
            )

        return "\n".join(summary)

    @staticmethod
    def _get_risk_category(score: float) -> str:
        """Returns standard heat risk category from numerical risk score."""
        if score >= 75.0:
            return "EXTREME / CRITICAL"
        elif score >= 55.0:
            return "HIGH RISK"
        elif score >= 35.0:
            return "MODERATE"
        else:
            return "LOW RISK"

    def export_geojson(
        self,
        optimization_result: OptimizationResult,
        zones: List[UrbanZone],
    ) -> Dict[str, Any]:
        """
        Exports optimization and What-If simulation results as standard GeoJSON FeatureCollection
        for immediate display in Mapbox, Leaflet, or Kepler.gl map frontends.
        """
        zone_report_map = {zr.zone_id: zr for zr in optimization_result.zone_reports}
        features = []

        for z in zones:
            zr = zone_report_map.get(z.zone_id)
            lat = z.lat if z.lat is not None else 0.0
            lon = z.lon if z.lon is not None else 0.0

            properties = {
                "zone_id": z.zone_id,
                "zone_name": z.name,
                "zone_type": z.zone_type,
                "baseline_risk_score": z.current_risk_score,
                "projected_risk_score": zr.projected_risk_score if zr else z.current_risk_score,
                "risk_points_reduced": zr.risk_points_reduced if zr else 0.0,
                "risk_pct_reduced": zr.risk_pct_reduced if zr else 0.0,
                "vulnerable_population": z.vulnerable_population,
                "lives_protected": zr.lives_protected if zr else 0,
                "allocated_budget": zr.allocated_budget if zr else 0.0,
                "lives_protected_per_10k": zr.lives_protected_per_10k if zr else 0.0,
                "effective_temp_reduction_c": zr.effective_temp_reduction_c if zr else 0.0,
                "baseline_ambient_temp_c": z.baseline_ambient_temp_c,
                "baseline_surface_temp_c": z.baseline_surface_temp_c,
                "allocated_units": zr.allocated_units_by_type if zr else {},
            }

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": properties,
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "total_budget": optimization_result.total_budget,
                "total_cost_spent": optimization_result.total_cost_spent,
                "total_lives_protected": optimization_result.total_lives_protected,
                "portfolio_lives_per_10k": optimization_result.lives_protected_per_10k_spent,
            },
            "features": features,
        }


# ============================================================================
# 7. SAMPLE DATA GENERATOR FOR TESTING & DEMONSTRATIONS
# ============================================================================

def create_sample_urban_zones() -> List[UrbanZone]:
    """
    Creates a realistic dataset of 6 diverse urban wards in a heat-vulnerable metropolis,
    spanning dense tin-roof settlements, vendor alleys, transit terminals, and avenues.
    """
    return [
        UrbanZone(
            zone_id="WARD-A-SLUM",
            name="Shanti Nagar Tin-Roof Informal Settlement",
            zone_type="informal_settlement",
            current_risk_score=88.5,
            baseline_ambient_temp_c=43.2,
            baseline_surface_temp_c=52.4,
            total_population=28000,
            vulnerable_population=9200,
            area_sq_km=0.85,
            tin_roof_pct=82.0,
            canopy_cover_pct=3.5,
            elderly_pct=14.0,
            outdoor_labor_pct=38.0,
            foot_traffic_level="High",
            max_cool_roof_households=1200,
            max_cooling_centers=3,
            max_misting_kiosks=6,
            max_shade_sails_streets=8,
            lat=19.0412,
            lon=72.8521,
        ),
        UrbanZone(
            zone_id="WARD-B-MARKET",
            name="Old City Central Bazaar & Vendor Corridors",
            zone_type="vendor_market",
            current_risk_score=79.2,
            baseline_ambient_temp_c=42.0,
            baseline_surface_temp_c=49.8,
            total_population=18500,
            vulnerable_population=6100,
            area_sq_km=0.65,
            tin_roof_pct=25.0,
            canopy_cover_pct=2.1,
            elderly_pct=11.0,
            outdoor_labor_pct=52.0,
            foot_traffic_level="Extreme",
            max_shade_sails_streets=14,
            max_misting_kiosks=8,
            max_cooling_centers=2,
            lat=19.0289,
            lon=72.8390,
        ),
        UrbanZone(
            zone_id="WARD-C-TRANSIT",
            name="Intercity Rail & Bus Transit Terminal Hub",
            zone_type="transit_hub",
            current_risk_score=76.8,
            baseline_ambient_temp_c=41.5,
            baseline_surface_temp_c=48.2,
            total_population=12000,
            vulnerable_population=4500,
            area_sq_km=0.90,
            tin_roof_pct=12.0,
            canopy_cover_pct=6.0,
            elderly_pct=9.0,
            outdoor_labor_pct=46.0,
            foot_traffic_level="Extreme",
            max_misting_kiosks=10,
            max_shade_sails_streets=6,
            max_cooling_centers=2,
            lat=19.0180,
            lon=72.8430,
        ),
        UrbanZone(
            zone_id="WARD-D-ELDERLY",
            name="Kalyan Nagar High-Density Residential Ward",
            zone_type="dense_residential",
            current_risk_score=71.4,
            baseline_ambient_temp_c=40.8,
            baseline_surface_temp_c=45.5,
            total_population=34000,
            vulnerable_population=7800,
            area_sq_km=1.40,
            tin_roof_pct=18.0,
            canopy_cover_pct=11.0,
            elderly_pct=24.0,  # High elderly cluster
            outdoor_labor_pct=12.0,
            foot_traffic_level="Medium",
            max_cooling_centers=5,
            max_cool_roof_households=450,
            lat=19.0550,
            lon=72.8680,
        ),
        UrbanZone(
            zone_id="WARD-E-AVENUE",
            name="Eastern Express Highway & Unshaded Arterial Corridor",
            zone_type="wide_avenue",
            current_risk_score=64.0,
            baseline_ambient_temp_c=42.6,
            baseline_surface_temp_c=51.0,
            total_population=15000,
            vulnerable_population=3200,
            area_sq_km=2.20,
            tin_roof_pct=8.0,
            canopy_cover_pct=4.2,  # Critically low canopy along wide avenue
            elderly_pct=8.0,
            outdoor_labor_pct=22.0,
            foot_traffic_level="Medium",
            max_forestry_km=5.0,
            max_misting_kiosks=5,
            lat=19.0620,
            lon=72.8910,
        ),
        UrbanZone(
            zone_id="WARD-F-SUBURB",
            name="Green Valley Planned Residential Sector",
            zone_type="residential_suburb",
            current_risk_score=38.2,
            baseline_ambient_temp_c=36.5,
            baseline_surface_temp_c=39.0,
            total_population=22000,
            vulnerable_population=1800,
            area_sq_km=3.10,
            tin_roof_pct=4.0,
            canopy_cover_pct=28.0,  # Well shaded
            elderly_pct=12.0,
            outdoor_labor_pct=6.0,
            foot_traffic_level="Low",
            max_forestry_km=3.0,
            lat=19.0800,
            lon=72.9150,
        ),
    ]


if __name__ == "__main__":
    import json

    print("=" * 80)
    print(" TERRA07 URBAN HEAT MITIGATION & RESOURCE ALLOCATION OPTIMIZER")
    print("=" * 80)

    optimizer = InterventionOptimizer()
    zones = create_sample_urban_zones()

    # 1. PRIORITY RANKING BY URGENCY
    print("\n>>> STEP 1: PRIORITY RANKING BY URGENCY")
    print("-" * 80)
    ranked = optimizer.rank_zones_by_urgency(zones)
    for r in ranked:
        top_rec = r.recommended_interventions[0] if r.recommended_interventions else None
        rec_desc = f"{top_rec.intervention_name} (${top_rec.unit_cost:,.0f}/{top_rec.unit_name})" if top_rec else "None"
        print(f"Rank #{r.rank} | {r.zone_name[:38]:<38} | Urgency: {r.urgency_score:5.1f} | Risk: {r.current_risk_score:5.1f} | Vuln Pop: {r.vulnerable_headcount:5,}")
        print(f"       Primary Drivers: {'; '.join(r.primary_risk_drivers[:2])}")
        print(f"       Top Action:      {rec_desc} (Suitability: {top_rec.suitability_score:.0f}%)")

    # 2. BUDGET-CONSTRAINED OPTIMIZATION ($100k & $500k)
    for budget in [100000.0, 500000.0]:
        print(f"\n>>> STEP 2: KNAPSACK ALLOCATION OPTIMIZATION (BUDGET: ${budget:,.0f})")
        print("-" * 80)
        res = optimizer.optimize_budget(zones, total_budget=budget, objective="balanced")

        print(f"Authorized Budget:         ${res.total_budget:,.2f}")
        print(f"Total Invested:            ${res.total_cost_spent:,.2f} ({res.budget_utilization_pct:.1f}% utilization)")
        print(f"Unallocated Reserve:       ${res.remaining_budget:,.2f}")
        print(f"Vulnerable Lives Shielded: {res.total_lives_protected:,} persons")
        print(f"Cumulative Cooling:        {res.total_effective_heat_reduction_deg_c:.2f}°C")
        print(f"Average Risk Drop:         -{res.average_risk_reduction_points:.2f} points")
        print(f"ROI (Lives per $10k):      {res.lives_protected_per_10k_spent:.1f} lives / $10,000")
        print(f"ROI (Thermal Cooling):     {res.degrees_celsius_reduction_per_1000_spent:.4f}°C / $1,000 spent")

        print("\nDeployments by Intervention:")
        for int_id, count in res.units_by_intervention.items():
            if count > 0:
                spec = INTERVENTION_CATALOG[int_id]
                spent = res.spend_by_intervention[int_id]
                lives = res.lives_protected_by_intervention[int_id]
                print(f"  * {spec.name:<52} : {count:3d} {spec.unit_name:<9} | Cost: ${spent:8,.0f} | Lives: {lives:5,}")

    # 3. WHAT-IF POST-INTERVENTION RECALCULATION
    print("\n>>> STEP 3: SIMULATED 'WHAT-IF' MICROCLIMATE & RISK RECALCULATION")
    print("-" * 80)
    top_slum = zones[0]
    test_interventions = {
        InterventionType.COOL_ROOF.value: 120,
        InterventionType.COOLING_CENTER.value: 2,
        InterventionType.MISTING_KIOSKS.value: 4,
        InterventionType.SHADE_SAILS.value: 3,
    }
    what_if = optimizer.simulate_what_if(top_slum, test_interventions)
    print(f"Zone Target:              {what_if.zone_name}")
    print(f"Total Investment:         ${what_if.total_cost:,.2f}")
    print(f"Interventions Deployed:   {what_if.deployed_interventions}")
    print(f"Baseline Risk Score:      {what_if.baseline_risk_score:.1f} / 100")
    print(f"Projected Risk Score:     {what_if.projected_risk_score:.1f} / 100 ({what_if.risk_level_transition})")
    print(f"Risk Score Reduction:     -{what_if.risk_score_reduction:.1f} points (-{what_if.risk_reduction_pct:.1f}%)")
    print(f"Ambient Temperature:      {what_if.baseline_ambient_temp_c:.1f}°C -> {what_if.projected_ambient_temp_c:.1f}°C (-{what_if.ambient_temp_reduction_c:.1f}°C)")
    print(f"Surface Temperature:      {what_if.baseline_surface_temp_c:.1f}°C -> {what_if.projected_surface_temp_c:.1f}°C (-{what_if.surface_temp_reduction_c:.1f}°C)")
    print(f"Vulnerable Lives Shielded:{what_if.lives_protected:,} of {what_if.vulnerable_headcount:,} ({what_if.vulnerable_protection_coverage_pct:.1f}% coverage)")
    print("=" * 80)

