"""
TERRA07 Heat-Risk Intelligence Engine - Data Schemas & API Models
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum


# ---------------------------------------------------------
# Common & GeoJSON Primitives
# ---------------------------------------------------------

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class GeoJSONGeometry(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str = Field(..., description="Geometry type e.g., Polygon, MultiPolygon, LineString, Point")
    coordinates: Any = Field(..., description="GeoJSON coordinates hierarchy")


class GeoJSONFeature(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------
# 1. Root / System Metadata Schemas
# ---------------------------------------------------------

class RootMetadataResponse(BaseModel):
    system: str = Field(..., description="System brand name")
    project: str = Field(..., description="Hackathon track and project designation")
    team: str = Field(..., description="Team identifier")
    lead: str = Field(..., description="Agent lead specialty")
    version: str = Field("1.0.0", description="API version")
    status: str = Field("healthy", description="Current backend operational health")
    city: str = Field(..., description="Target urban focus area")
    description: str = Field(..., description="High-level mission statement")
    endpoints: Dict[str, str] = Field(default_factory=dict, description="Directory of primary REST endpoints")
    timestamp: str = Field(..., description="ISO 8601 server timestamp")


# ---------------------------------------------------------
# 2. City Overview Schemas
# ---------------------------------------------------------

class VulnerablePopulationBreakdown(BaseModel):
    elderly_count: int = Field(..., description="Count of population aged 65+")
    children_under_5_count: int = Field(..., description="Count of infants and young children (<5 yrs)")
    outdoor_laborers_count: int = Field(..., description="Informal/outdoor construction & street vendors")
    slum_and_informal_settlement_count: int = Field(..., description="Residents without thermal insulation/AC")
    total_vulnerable: int = Field(..., description="Total combined high-risk individuals")
    vulnerable_ratio_pct: float = Field(..., description="Percentage of total urban population deemed high vulnerability")


class WardExtremeSummary(BaseModel):
    ward_id: str
    ward_name: str
    zone: str
    mean_lst_celsius: float
    heat_risk_score: float
    risk_level: str


class CityOverviewResponse(BaseModel):
    city_name: str
    total_population: int
    average_heat_risk: float = Field(..., description="Citywide mean Heat Vulnerability Index (0-100 scale)")
    average_surface_temp_celsius: float
    ambient_air_temp_celsius: float
    hottest_ward: WardExtremeSummary
    coolest_ward: WardExtremeSummary
    most_vulnerable_population: VulnerablePopulationBreakdown
    active_cooling_centers_count: int
    active_hydration_points_count: int
    total_wards_count: int
    total_streets_count: int
    city_alert_level: str = Field(..., description="e.g. Green, Yellow, Orange, Red Alert")
    alert_advisory: str
    last_updated: str


# ---------------------------------------------------------
# 3. Ward Schemas
# ---------------------------------------------------------

class RiskTier(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    EXTREME = "Extreme"


class WardEnvironmentalMetrics(BaseModel):
    mean_lst_celsius: float = Field(..., description="Mean Land Surface Temperature in °C")
    max_lst_celsius: float
    min_lst_celsius: float
    ndvi_vegetation_index: float = Field(..., description="Normalized Difference Vegetation Index (-1 to 1)")
    ndbi_builtup_index: float = Field(..., description="Normalized Difference Built-up Index (-1 to 1)")
    surface_albedo: float = Field(..., description="Average surface reflectivity (0 to 1)")
    tree_canopy_pct: float = Field(..., description="Tree canopy coverage percentage")
    impervious_surface_pct: float = Field(..., description="Paved/impervious surface fraction")


class WardDemographicMetrics(BaseModel):
    total_population: int
    population_density_per_km2: float
    elderly_pct: float = Field(..., description="Elderly (65+) ratio")
    children_pct: float = Field(..., description="Children under 5 ratio")
    outdoor_workers_pct: float = Field(..., description="Outdoor laborer ratio")
    slum_households_pct: float = Field(..., description="Informal settlement/slum housing ratio")
    poverty_ratio_pct: float
    baseline_heat_illness_rate: float = Field(..., description="Reported heat exhaustion per 10k population")


class WardAdaptiveCapacityMetrics(BaseModel):
    ac_penetration_pct: float = Field(..., description="Percentage of households with active air conditioning")
    cooling_centers_count: int
    hydration_points_count: int
    hospitals_and_clinics_count: int
    distance_to_nearest_hospital_m: float
    tree_planting_potential_pct: float


class WardProfile(BaseModel):
    ward_id: str
    ward_name: str
    zone: str
    area_km2: float
    heat_risk_score: float = Field(..., ge=0.0, le=100.0, description="Heat Vulnerability Index (0-100)")
    risk_level: RiskTier
    risk_percentile: float = Field(..., description="Percentile relative to all city wards (0-100)")
    environmental: WardEnvironmentalMetrics
    demographics: WardDemographicMetrics
    adaptive_capacity: WardAdaptiveCapacityMetrics
    dominant_heat_drivers: List[str] = Field(default_factory=list)
    top_recommended_interventions: List[str] = Field(default_factory=list)
    geometry: Optional[GeoJSONGeometry] = None


class WardListResponse(BaseModel):
    total_count: int
    city_average_risk: float
    wards: List[WardProfile]
    geojson: Optional[GeoJSONFeatureCollection] = None


# ---------------------------------------------------------
# 4. Street Schemas (Human-Scale Microclimate)
# ---------------------------------------------------------

class StreetSegment(BaseModel):
    street_id: str
    street_name: str
    ward_id: str
    ward_name: str
    length_meters: float
    mean_radiant_temp_celsius: float = Field(..., description="Tmrt: Mean Radiant Temperature at pedestrian level")
    surface_temp_celsius: float
    shade_ratio: float = Field(..., ge=0.0, le=1.0, description="Proportion of street under canopy or building shade (0.0 to 1.0)")
    sky_view_factor: float = Field(..., ge=0.0, le=1.0, description="Sky View Factor SVF (0.0=dense canyon, 1.0=open sky)")
    aspect_ratio_h_w: float = Field(..., description="Building height to street width ratio (H/W)")
    pedestrian_heat_risk: float = Field(..., ge=0.0, le=100.0, description="Microclimate pedestrian risk score")
    risk_level: RiskTier
    pedestrian_volume: str = Field(..., description="Low, Moderate, High, Critical Foot-traffic")
    tree_count: int
    has_water_misting: bool = False
    geometry: GeoJSONGeometry = Field(..., description="GeoJSON LineString coordinates")


class StreetListResponse(BaseModel):
    total_count: int
    average_shade_ratio: float
    average_radiant_temp: float
    streets: List[StreetSegment]
    geojson: Optional[GeoJSONFeatureCollection] = None


# ---------------------------------------------------------
# 5. Explainable AI (XAI) Schemas
# ---------------------------------------------------------

class XAIFactorAttribution(BaseModel):
    factor_name: str = Field(..., description="Normalized factor key e.g. surface_temperature")
    display_name: str = Field(..., description="Human friendly metric name")
    category: str = Field(..., description="Hazard, Exposure, or Vulnerability/Capacity")
    raw_value: float = Field(..., description="Actual measured or modeled value")
    raw_unit: str = Field(..., description="Unit of measurement e.g. °C, %, index")
    attribution_points: float = Field(..., description="SHAP-style additive points to final risk score (+/- points)")
    percentage_contribution: float = Field(..., description="Share of net positive risk driver (0-100%)")
    description: str = Field(..., description="Contextual explanation of how this factor influences heat stress")


class XAIExplanationResponse(BaseModel):
    entity_type: str = Field(..., description="'ward' or 'street'")
    entity_id: str
    entity_name: str
    overall_heat_risk: float = Field(..., description="Calculated composite risk score (0-100)")
    risk_level: RiskTier
    baseline_city_risk: float = Field(..., description="Reference citywide baseline risk")
    risk_excess_above_baseline: float
    primary_driver: str = Field(..., description="Main culprit causing excess heat risk")
    secondary_driver: str
    factor_attributions: List[XAIFactorAttribution]
    factors: List[XAIFactorAttribution] = Field(default_factory=list, description="Direct factors list for XAI breakdown")
    dominant_factor: str = Field("", description="Primary dominant heat driver")
    composite_heat_risk: float = Field(0.0, description="Overall composite risk index (0-100)")
    primary_bottleneck: str = Field("", description="Highest-leverage actionable bottleneck intervention")
    natural_language_diagnosis: str = Field(..., description="Comprehensive natural language executive brief")
    actionable_policy_insight: str = Field(..., description="Targeted municipal or clinical recommendation")
    waterfall_chart: Optional[Dict[str, Any]] = Field(default=None, description="Waterfall chart series dataset")
    radar_chart: Optional[Dict[str, Any]] = Field(default=None, description="Radar/spider chart dataset")


# ---------------------------------------------------------
# 6. Intervention Recommendation & What-If Schemas
# ---------------------------------------------------------

class InterventionPriority(str, Enum):
    BALANCED = "balanced"
    VULNERABLE_POPULATIONS = "vulnerable_populations"
    COOLING_SPEED = "cooling_speed"
    MAXIMUM_TEMP_DROP = "maximum_temp_drop"
    STREET_WALKABILITY = "street_walkability"


class InterventionRequest(BaseModel):
    ward_ids: Optional[List[str]] = Field(default=None, description="Optional filter of specific ward IDs. If empty, citywide.")
    budget_inr_lakhs: float = Field(default=500.0, ge=0.0, description="Total budget in INR Lakhs")
    budget_usd: Optional[float] = Field(default=None, description="Alternative budget in USD")
    priority_focus: InterventionPriority = Field(default=InterventionPriority.BALANCED)
    max_interventions: int = Field(default=10, ge=1, le=50)


class InterventionItem(BaseModel):
    intervention_id: str
    intervention_type: str = Field(..., description="e.g. Cool Roof Coating, Miyawaki Pocket Forest, Shaded Bus Corridors")
    category: str = Field(..., description="Nature-Based, Structural, Behavioral, Infrastructure")
    ward_id: str
    ward_name: str
    zone: str
    cost_inr_lakhs: float
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    temp_reduction_celsius: float = Field(..., description="Projected local temperature reduction")
    risk_score_reduction: float = Field(..., description="Projected drop in HVI score")
    population_protected: int
    lives_protected_count: int = Field(default=0, description="Alias for population_protected")
    roi_cost_effectiveness_score: float = Field(..., description="Points of risk reduced per Lakh INR spent")
    implementation_time_months: int
    co_benefits: List[str] = Field(default_factory=list)
    description: str


class AffectedZoneItem(BaseModel):
    zone_id: str
    zone_name: str
    baseline_risk_score: float
    projected_risk_score: float
    baseline_surface_temp: float
    projected_surface_temp: float
    risk_reduction_pct: float


class WhatIfSimulationModel(BaseModel):
    affected_zones: List[AffectedZoneItem] = Field(default_factory=list)
    city_baseline_average_risk: float = 0.0
    city_projected_average_risk: float = 0.0
    net_risk_reduction_points: float = 0.0


class InterventionResponse(BaseModel):
    priority_focus: str
    total_budget_allocated_lakhs: float
    total_budget_requested_lakhs: float
    remaining_budget_lakhs: float
    total_cost_usd: float = Field(default=0.0, description="Total allocated cost in USD")
    remaining_budget_usd: float = Field(default=0.0, description="Remaining budget in USD")
    total_population_protected: int
    lives_protected: int = Field(default=0, description="Total lives/population protected")
    average_citywide_risk_drop: float
    recommendations_count: int
    recommendations: List[InterventionItem]
    allocated_interventions: List[InterventionItem] = Field(default_factory=list, description="Alias for recommendations")
    what_if_before_after: Dict[str, Any] = Field(..., description="Citywide comparative baseline vs post-intervention metrics")
    what_if_simulation: Optional[WhatIfSimulationModel] = Field(default=None, description="Detailed what-if simulation model")


# ---------------------------------------------------------
# 7. Cool-Path Routing Schemas
# ---------------------------------------------------------

class VulnerabilityProfile(str, Enum):
    STANDARD = "standard"
    ELDERLY = "elderly"
    CHILD = "child"
    OUTDOOR_LABORER = "outdoor_laborer"
    CARDIAC_PATIENT = "cardiac_patient"


class CoolPathRequest(BaseModel):
    start: Optional[Coordinates] = Field(default=None, description="Starting point (start alias)")
    end: Optional[Coordinates] = Field(default=None, description="Destination point (end alias)")
    origin: Optional[Coordinates] = Field(default=None, description="Starting location latitude and longitude")
    destination: Optional[Coordinates] = Field(default=None, description="Target destination latitude and longitude")
    preference: Optional[str] = Field(default="cool", description="'cool' or 'shortest'")
    departure_hour: int = Field(default=14, ge=0, le=23, description="Hour of departure (0-23)")
    max_detour_factor: float = Field(default=1.5, ge=1.0, le=3.0, description="Acceptable detour factor")
    vulnerability_profile: VulnerabilityProfile = Field(default=VulnerabilityProfile.STANDARD)

    @model_validator(mode="after")
    def validate_endpoints(self):
        orig = self.origin or self.start
        dest = self.destination or self.end
        if not orig:
            raise ValueError("Must provide either 'origin' or 'start' coordinates.")
        if not dest:
            raise ValueError("Must provide either 'destination' or 'end' coordinates.")
        if not self.origin:
            self.origin = orig
        if not self.destination:
            self.destination = dest
        return self


class RouteStep(BaseModel):
    step_number: int
    instruction: str
    street_name: str
    distance_meters: float
    shade_ratio: float
    radiant_temp_celsius: float
    risk_tier: RiskTier
    thermal_advisory: str = Field(default="Moderate Thermal Stress - Walk on shaded side", description="Actionable step guidance")


class RouteDetail(BaseModel):
    route_type: str = Field(..., description="'shortest' or 'cool_path'")
    total_distance_meters: float
    estimated_walking_minutes: float
    average_shade_ratio: float
    average_heat_risk: float = Field(default=42.0, description="Average pedestrian heat risk along route")
    peak_radiant_temp_celsius: float
    average_radiant_temp_celsius: float
    heat_stress_exposure_index: float = Field(..., description="Cumulative physiological heat strain dose")
    safety_tier: str
    steps: List[RouteStep]
    geometry: GeoJSONGeometry = Field(..., description="GeoJSON LineString route path")


class HydrationCheckpoint(BaseModel):
    name: str
    type: str
    distance_from_route_m: float
    coordinates: Coordinates


class CoolPathResponse(BaseModel):
    origin_node_id: str = Field(default="NODE_ORIGIN")
    destination_node_id: str = Field(default="NODE_DEST")
    shortest_path: RouteDetail
    cool_path: RouteDetail
    delta_distance_meters: float
    delta_distance_pct: float
    heat_stress_reduction_pct: float = Field(..., description="Percentage reduction in total thermal strain dose")
    heat_exposure_reduction_pct: float = Field(default=0.0, description="Alias for heat stress reduction pct")
    shade_increase_pct: float
    temperature_difference_celsius: float
    pedestrian_recommendation: str
    nearby_hydration_checkpoints: List[HydrationCheckpoint]


# ---------------------------------------------------------
# 8. Dynamic Heat Scenario Simulation Schemas
# ---------------------------------------------------------

class ScenarioType(str, Enum):
    CLIMATE_SURGE_2C = "climate_surge_2c"
    EXTREME_HEATWAVE_4C = "extreme_heatwave_4c"
    EXTREME_HEATWAVE = "extreme_heatwave"
    GRID_FAILURE_BLACKOUT = "grid_failure_blackout"
    TREE_CANOPY_EXPANSION_20PCT = "tree_canopy_expansion_20pct"
    COOL_ROOF_SATURATION_50PCT = "cool_roof_saturation_50pct"
    CUSTOM = "custom"


class ScenarioSimulateRequest(BaseModel):
    scenario: Optional[str] = Field(default=None, description="Scenario string alias")
    scenario_type: Optional[ScenarioType] = Field(default=None, description="Typed scenario type")
    temperature_delta_c: Optional[float] = Field(default=None, description="Temperature shift in °C")
    ambient_surge_celsius: Optional[float] = Field(default=None, description="Ambient surge in °C")
    grid_failure: Optional[bool] = Field(default=None, description="Grid failure boolean flag")
    grid_power_available_pct: Optional[float] = Field(default=None, description="1.0 = normal, 0.0 = blackout")
    canopy_loss_pct: Optional[float] = Field(default=None, description="Canopy loss %")
    vegetation_increase_pct: Optional[float] = Field(default=None, description="Tree canopy increase %")
    cool_roof_adoption_pct: Optional[float] = Field(default=None, description="Cool roof adoption %")
    target_ward_ids: Optional[List[str]] = Field(default=None, description="Target ward subset")


class WardSimulationImpact(BaseModel):
    ward_id: str
    ward_name: str
    zone: str
    baseline_risk: float
    simulated_risk: float
    risk_delta: float
    baseline_level: RiskTier
    simulated_level: RiskTier
    is_newly_extreme: bool
    estimated_excess_heat_cases: int
    primary_stress_factor: str


class ScenarioSimulateResponse(BaseModel):
    scenario_name: str
    scenario_description: str
    baseline_city_average_risk: float
    simulated_city_average_risk: float
    city_baseline_average_risk: float = Field(default=0.0, description="Alias for baseline_city_average_risk")
    city_new_average_risk: float = Field(default=0.0, description="Alias for simulated_city_average_risk")
    city_average_risk_delta: float
    baseline_extreme_wards_count: int
    simulated_extreme_wards_count: int
    total_population_at_extreme_risk: int
    projected_daily_hospital_admissions: int
    alert_escalation: str = Field(..., description="Alert escalation level")
    most_impacted_wards: List[WardSimulationImpact]
    impacted_wards: List[WardSimulationImpact] = Field(default_factory=list, description="Alias for most_impacted_wards")
    operational_emergency_directives: List[str]


# ---------------------------------------------------------
# 9. Public Advisory Schemas
# ---------------------------------------------------------

class CoolingCenterItem(BaseModel):
    center_id: str
    name: str
    facility_type: str = Field(..., description="Facility category")
    address: str
    coordinates: Coordinates
    distance_meters: float
    walking_time_minutes: int
    operating_hours: str
    capacity_persons: int
    capacity: int = Field(default=200, description="Alias for capacity_persons")
    has_medical_staff: bool
    has_ac: bool = Field(default=True, description="AC status")
    lat: float = Field(default=23.0225, description="Latitude")
    lon: float = Field(default=72.5714, description="Longitude")
    phone_contact: str


class HydrationPointItem(BaseModel):
    point_id: str
    name: str
    water_source_type: str = Field(..., description="Water source")
    coordinates: Coordinates
    distance_meters: float
    lat: float = Field(default=23.0225, description="Latitude")
    lon: float = Field(default=72.5714, description="Longitude")
    status: str
    is_free: bool


class PublicAdviceResponse(BaseModel):
    query_coordinates: Coordinates
    matched_ward_id: str
    matched_ward_name: str
    current_heat_risk_score: float
    current_risk_level: RiskTier
    danger_tier: str = Field(default="High", description="Danger tier category (Extreme, Severe, High, Moderate, Low)")
    current_ambient_temp_celsius: float
    current_feels_like_celsius: float
    safe_outdoor_minutes: int = Field(default=25, description="Safe outdoor walking exposure minutes before heat strain")
    heat_alert_banner: str
    personalized_clinical_advice: List[str]
    immediate_actions_to_take: List[str]
    high_risk_symptoms_warning: List[str]
    nearest_cooling_centers: List[CoolingCenterItem]
    nearest_hydration_points: List[HydrationPointItem]
    emergency_helpline_numbers: Dict[str, str]


# ---------------------------------------------------------
# 10. Generic Error Schema
# ---------------------------------------------------------

class ErrorResponse(BaseModel):
    status_code: int
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
