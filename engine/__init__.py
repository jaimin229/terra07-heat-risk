"""
Engine module initialization for TERRA07.
Heat-Risk Mapping at Human Scale.
"""

# Cool Routing
try:
    from engine.cool_router import (
        CoolRouter,
        IntersectionNode,
        StreetSegmentEdge,
        TurnDirectionStep,
        RouteResult,
        RouteComparison,
    )
except ImportError:
    pass

# Socio-Demographic Vulnerability Modeling (Agent 3)
from engine.vulnerability_model import (
    SocioDemographicVulnerabilityModel,
    VulnerabilityTier,
    RoofMaterialType,
    OutdoorOccupationType,
    AgeDependencyMetrics,
    OccupationalDemographics,
    CoolingInfrastructureMetrics,
    HousingStockMetrics,
    HealthcareAccessMetrics,
    HealthPrevalenceMetrics,
    SVIWeights,
    SVIDetailedScore,
    VulnerablePopulationCounts,
    HeatExposureDose,
    CitizenPersona,
    PersonaAssessmentResult,
    calculate_age_dependency_index,
    calculate_occupational_heat_stress,
    calculate_cooling_inequality_deficit,
    calculate_housing_heat_trap_factor,
    calculate_healthcare_accessibility_deficit,
    calculate_preexisting_health_vulnerability,
    calculate_svi,
    calculate_vulnerable_population_counts,
    calculate_person_hours_dangerous_exposure,
    assess_citizen_persona,
    get_standard_archetype_personas,
)

# Explainable AI & Driver Breakdown (Agent 4)
from engine.xai_attribution import (
    HeatRiskDriver,
    DriverWeights,
    NormalizationThresholds,
    RawDriverValues,
    FeatureAttribution,
    BottleneckLeveragePoint,
    WaterfallChartStep,
    WaterfallChartData,
    RadarAxis,
    RadarChartData,
    XAIDiagnosticReport,
    AdditiveAttributionEngine,
    ShapleyAttributionEngine,
    DiagnosticNarrativeGenerator,
    BottleneckLeverageIdentifier,
    VisualizationDataFormatter,
    HeatRiskXAIExplainer,
    explain_heat_risk,
)

__all__ = [
    # Routing
    "CoolRouter",
    "IntersectionNode",
    "StreetSegmentEdge",
    "TurnDirectionStep",
    "RouteResult",
    "RouteComparison",
    # Vulnerability Model
    "SocioDemographicVulnerabilityModel",
    "VulnerabilityTier",
    "RoofMaterialType",
    "OutdoorOccupationType",
    "AgeDependencyMetrics",
    "OccupationalDemographics",
    "CoolingInfrastructureMetrics",
    "HousingStockMetrics",
    "HealthcareAccessMetrics",
    "HealthPrevalenceMetrics",
    "SVIWeights",
    "SVIDetailedScore",
    "VulnerablePopulationCounts",
    "HeatExposureDose",
    "CitizenPersona",
    "PersonaAssessmentResult",
    "calculate_age_dependency_index",
    "calculate_occupational_heat_stress",
    "calculate_cooling_inequality_deficit",
    "calculate_housing_heat_trap_factor",
    "calculate_healthcare_accessibility_deficit",
    "calculate_preexisting_health_vulnerability",
    "calculate_svi",
    "calculate_vulnerable_population_counts",
    "calculate_person_hours_dangerous_exposure",
    "assess_citizen_persona",
    "get_standard_archetype_personas",
    # Explainable AI (Agent 4)
    "HeatRiskDriver",
    "DriverWeights",
    "NormalizationThresholds",
    "RawDriverValues",
    "FeatureAttribution",
    "BottleneckLeveragePoint",
    "WaterfallChartStep",
    "WaterfallChartData",
    "RadarAxis",
    "RadarChartData",
    "XAIDiagnosticReport",
    "AdditiveAttributionEngine",
    "ShapleyAttributionEngine",
    "DiagnosticNarrativeGenerator",
    "BottleneckLeverageIdentifier",
    "VisualizationDataFormatter",
    "HeatRiskXAIExplainer",
    "explain_heat_risk",
]

