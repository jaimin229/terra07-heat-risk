"""
TERRA07 Heat-Risk Intelligence Engine - RESTful API Routes
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse

from backend.data_store import store
from backend.schemas import (
    CityOverviewResponse, WardExtremeSummary, VulnerablePopulationBreakdown,
    WardProfile, WardListResponse, GeoJSONFeatureCollection, GeoJSONFeature,
    StreetSegment, StreetListResponse,
    XAIExplanationResponse,
    InterventionRequest, InterventionResponse,
    CoolPathRequest, CoolPathResponse,
    ScenarioSimulateRequest, ScenarioSimulateResponse,
    PublicAdviceResponse,
    CoolingCenterItem, HydrationPointItem, Coordinates
)
from backend.engine import (
    explain_entity, router_engine, recommend_interventions,
    simulate_heat_scenario, generate_public_advice, haversine_distance_meters
)

router = APIRouter(prefix="/api", tags=["Heat-Risk Intelligence"])


# ---------------------------------------------------------
# 1. GET /api/overview
# ---------------------------------------------------------

@router.get(
    "/overview",
    response_model=CityOverviewResponse,
    summary="Citywide Heat Risk & Vulnerability Summary",
    description="Provides an executive synthesis of citywide population, mean heat risk, extreme hotspot wards, vulnerable demographics, and active relief infrastructure."
)
async def get_city_overview() -> CityOverviewResponse:
    if not store._initialized:
        store.initialize()

    wards = list(store.wards.values())
    if not wards:
        raise HTTPException(status_code=500, detail="City dataset not initialized.")

    total_pop = sum(w["demographics"]["total_population"] for w in wards)
    scores = [w["heat_risk_score"] for w in wards]
    lst_temps = [w["environmental"]["mean_lst_celsius"] for w in wards]

    avg_risk = round(sum(scores) / len(scores), 1)
    avg_lst = round(sum(lst_temps) / len(lst_temps), 1)

    # Extremes
    hottest = max(wards, key=lambda x: x["environmental"]["mean_lst_celsius"])
    coolest = min(wards, key=lambda x: x["environmental"]["mean_lst_celsius"])

    # Demographics
    elderly = sum(int(w["demographics"]["total_population"] * (w["demographics"]["elderly_pct"] / 100.0)) for w in wards)
    children = sum(int(w["demographics"]["total_population"] * (w["demographics"]["children_pct"] / 100.0)) for w in wards)
    laborers = sum(int(w["demographics"]["total_population"] * (w["demographics"]["outdoor_workers_pct"] / 100.0)) for w in wards)
    slum_pop = sum(int(w["demographics"]["total_population"] * (w["demographics"]["slum_households_pct"] / 100.0)) for w in wards)
    total_vuln = int(elderly * 0.8 + children * 0.8 + laborers * 0.7 + slum_pop * 0.6)
    vuln_pct = round((total_vuln / max(1, total_pop)) * 100.0, 1)

    # City alert level based on average risk and temperature
    if avg_lst >= 44.0 or avg_risk >= 70.0:
        alert = "Red Alert (Severe Heatwave Emergency)"
        advisory = "Severe heat stress conditions citywide. Emergency Heat Action Plan fully activated. Avoid open-air travel 11:30-16:30."
    elif avg_lst >= 42.0 or avg_risk >= 55.0:
        alert = "Orange Alert (High Heatwave Stress)"
        advisory = "Elevated ambient radiant load. Outdoor workers and elderly must observe active hydration and shaded rest."
    else:
        alert = "Yellow Alert (Moderate Heat Advisory)"
        advisory = "Normal summer temperature conditions. Hydration checkpoints open across all municipal zones."

    return CityOverviewResponse(
        city_name="Ahmedabad Metropolitan Region",
        total_population=total_pop,
        average_heat_risk=avg_risk,
        average_surface_temp_celsius=avg_lst,
        ambient_air_temp_celsius=round(avg_lst - 3.4, 1),
        hottest_ward=WardExtremeSummary(
            ward_id=hottest["ward_id"],
            ward_name=hottest["ward_name"],
            zone=hottest["zone"],
            mean_lst_celsius=hottest["environmental"]["mean_lst_celsius"],
            heat_risk_score=hottest["heat_risk_score"],
            risk_level=hottest["risk_level"]
        ),
        coolest_ward=WardExtremeSummary(
            ward_id=coolest["ward_id"],
            ward_name=coolest["ward_name"],
            zone=coolest["zone"],
            mean_lst_celsius=coolest["environmental"]["mean_lst_celsius"],
            heat_risk_score=coolest["heat_risk_score"],
            risk_level=coolest["risk_level"]
        ),
        most_vulnerable_population=VulnerablePopulationBreakdown(
            elderly_count=elderly,
            children_under_5_count=children,
            outdoor_laborers_count=laborers,
            slum_and_informal_settlement_count=slum_pop,
            total_vulnerable=total_vuln,
            vulnerable_ratio_pct=vuln_pct
        ),
        active_cooling_centers_count=len(store.cooling_centers),
        active_hydration_points_count=len(store.hydration_points),
        total_wards_count=len(wards),
        total_streets_count=len(store.streets),
        city_alert_level=alert,
        alert_advisory=advisory,
        last_updated=datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------
# 2. GET /api/wards & GET /api/wards/{ward_id}
# ---------------------------------------------------------

@router.get(
    "/wards",
    response_model=Union[WardListResponse, GeoJSONFeatureCollection],
    summary="List All Wards or Query GeoJSON",
    description="Retrieve comprehensive risk metrics, environmental sensors, demographic indices, and polygon geometries for municipal wards."
)
async def get_wards(
    zone: Optional[str] = Query(None, description="Filter by administrative zone (e.g. Central, East, West, North, South)"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum Heat Vulnerability Index threshold"),
    search: Optional[str] = Query(None, description="Search keyword matching ward name"),
    format: Optional[str] = Query("json", description="'json' for structured response or 'geojson' for standard GIS FeatureCollection")
):
    if not store._initialized:
        store.initialize()

    filtered = list(store.wards.values())

    if zone:
        filtered = [w for w in filtered if zone.lower() in w["zone"].lower()]
    if min_risk is not None:
        filtered = [w for w in filtered if w["heat_risk_score"] >= min_risk]
    if search:
        s = search.lower()
        filtered = [w for w in filtered if s in w["ward_name"].lower() or s in w["ward_id"].lower()]

    scores = [w["heat_risk_score"] for w in filtered]
    avg_risk = round(sum(scores) / max(1, len(scores)), 1) if scores else 0.0

    # Build GeoJSON FeatureCollection
    features = []
    for w in filtered:
        features.append(GeoJSONFeature(
            type="Feature",
            id=w["ward_id"],
            geometry=w["geometry"],
            properties={
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "zone": w["zone"],
                "area_km2": w["area_km2"],
                "heat_risk_score": w["heat_risk_score"],
                "risk_level": w["risk_level"],
                "risk_percentile": w["risk_percentile"],
                "mean_lst_celsius": w["environmental"]["mean_lst_celsius"],
                "ndvi": w["environmental"]["ndvi_vegetation_index"],
                "population": w["demographics"]["total_population"],
                "slum_pct": w["demographics"]["slum_households_pct"],
                "ac_pct": w["adaptive_capacity"]["ac_penetration_pct"],
                "dominant_heat_drivers": w.get("dominant_heat_drivers", [])
            }
        ))
    fc = GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        metadata={"total_features": len(features), "city": "Ahmedabad"}
    )

    if format and format.lower() == "geojson":
        return fc

    ward_profiles = [WardProfile(**w) for w in filtered]
    return WardListResponse(
        total_count=len(ward_profiles),
        city_average_risk=avg_risk,
        wards=ward_profiles,
        geojson=fc
    )


@router.get(
    "/wards/{ward_id}",
    response_model=WardProfile,
    summary="Detailed Ward Profile",
    description="Retrieve granular heat vulnerability, satellite thermal indicators, and demographic vulnerability for a specific ward ID."
)
async def get_ward_by_id(
    ward_id: str = Path(..., description="Ward identifier (e.g. W01, W05) or ward name")
) -> WardProfile:
    if not store._initialized:
        store.initialize()

    ward = store.get_ward(ward_id)
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward '{ward_id}' not found."
        )

    return WardProfile(**ward)


# ---------------------------------------------------------
# 3. GET /api/streets
# ---------------------------------------------------------

@router.get(
    "/streets",
    response_model=Union[StreetListResponse, GeoJSONFeatureCollection],
    summary="Pedestrian & Human-Scale Street Microclimate",
    description="Fetch street-level segments with canopy shade ratios, Mean Radiant Temperature (Tmrt), Sky View Factor (SVF), and walking risk."
)
async def get_streets(
    ward_id: Optional[str] = Query(None, description="Filter street segments by ward ID"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum pedestrian heat risk"),
    shade_max: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum shade ratio (filter exposed streets)"),
    limit: int = Query(100, ge=1, le=500, description="Max street segments to return"),
    format: Optional[str] = Query("json", description="'json' or 'geojson'")
):
    if not store._initialized:
        store.initialize()

    filtered = store.streets
    if ward_id:
        target_w = store.get_ward(ward_id)
        target_id = target_w["ward_id"] if target_w else ward_id.upper()
        filtered = [s for s in filtered if s.get("ward_id") == target_id or s.get("destination_ward_id") == target_id]
    if min_risk is not None:
        filtered = [s for s in filtered if s["pedestrian_heat_risk"] >= min_risk]
    for s in filtered:
        if "shade_ratio" not in s:
            s["shade_ratio"] = s.get("tree_canopy_shading_ratio", 0.35)

    if shade_max is not None:
        filtered = [s for s in filtered if s["shade_ratio"] <= shade_max]

    filtered = filtered[:limit]

    shades = [s["shade_ratio"] for s in filtered]
    tmrts = [s.get("mean_radiant_temp_celsius", 42.0) for s in filtered]
    avg_shade = round(sum(shades) / max(1, len(shades)), 2) if shades else 0.0
    avg_tmrt = round(sum(tmrts) / max(1, len(tmrts)), 1) if tmrts else 0.0

    features = []
    for s in filtered:
        features.append(GeoJSONFeature(
            type="Feature",
            id=s["street_id"],
            geometry=s["geometry"],
            properties={
                "street_id": s["street_id"],
                "street_name": s["street_name"],
                "ward_id": s["ward_id"],
                "length_meters": s["length_meters"],
                "shade_ratio": s["shade_ratio"],
                "mean_radiant_temp_celsius": s.get("mean_radiant_temp_celsius", 42.0),
                "pedestrian_heat_risk": s["pedestrian_heat_risk"],
                "risk_level": s["risk_level"]
            }
        ))
    fc = GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        metadata={"total_segments": len(features)}
    )

    if format and format.lower() == "geojson":
        return fc

    street_models = [
        StreetSegment(
            street_id=s["street_id"],
            street_name=s["street_name"],
            ward_id=s["ward_id"],
            ward_name=s["ward_name"],
            length_meters=s["length_meters"],
            mean_radiant_temp_celsius=s.get("mean_radiant_temp_celsius", 42.0),
            surface_temp_celsius=s.get("surface_temp_celsius", 40.0),
            shade_ratio=s["shade_ratio"],
            sky_view_factor=s.get("sky_view_factor", 0.6),
            aspect_ratio_h_w=s.get("aspect_ratio_h_w", 1.2),
            pedestrian_heat_risk=s["pedestrian_heat_risk"],
            risk_level=s["risk_level"],
            pedestrian_volume=s.get("pedestrian_volume", "Moderate"),
            tree_count=s.get("tree_count", 20),
            has_water_misting=s.get("has_water_misting", False),
            geometry=s["geometry"]
        )
        for s in filtered
    ]
    return StreetListResponse(
        total_count=len(street_models),
        average_shade_ratio=avg_shade,
        average_radiant_temp=avg_tmrt,
        streets=street_models,
        geojson=fc
    )


# ---------------------------------------------------------
# 4. GET /api/explain/{entity_type}/{id}
# ---------------------------------------------------------

@router.get(
    "/explain/{entity_type}/{id}",
    response_model=XAIExplanationResponse,
    summary="Explainable AI (XAI) Driver Breakdown & Diagnosis",
    description="Calculates exact SHAP-style attribution percentages across hazard, exposure, vulnerability, and adaptive capacity with natural language synthesis."
)
async def get_xai_explanation(
    entity_type: str = Path(..., description="Entity classification: 'ward' or 'street'"),
    id: str = Path(..., description="Unique entity ID (e.g. W01, ST005, or ward name)")
) -> XAIExplanationResponse:
    if not store._initialized:
        store.initialize()

    try:
        explanation = explain_entity(entity_type=entity_type, entity_id=id)
        return explanation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"XAI calculation failure: {str(e)}")


# ---------------------------------------------------------
# 5. POST /api/interventions/recommend
# ---------------------------------------------------------

@router.post(
    "/interventions/recommend",
    response_model=InterventionResponse,
    summary="Ranked Mitigation Recommendations & Budget Allocation",
    description="Multi-objective knapsack optimizer prioritizing nature-based, reflective, and structural heat mitigations under budget constraints with what-if simulation."
)
async def post_recommend_interventions(payload: InterventionRequest) -> InterventionResponse:
    if not store._initialized:
        store.initialize()

    try:
        response = recommend_interventions(
            target_ward_ids=payload.ward_ids,
            budget_lakhs=payload.budget_inr_lakhs,
            priority=payload.priority_focus,
            max_items=payload.max_interventions
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed optimizing intervention allocation: {str(e)}"
        )


# ---------------------------------------------------------
# 6. POST /api/routing/cool-path
# ---------------------------------------------------------

@router.post(
    "/routing/cool-path",
    response_model=CoolPathResponse,
    summary="Calculate Shortest vs Cool Walking Path",
    description="Dijkstra routing comparing standard minimum distance path against shaded, heat-mitigated corridor path with cumulative thermal dose reduction."
)
async def post_cool_path_routing(payload: CoolPathRequest) -> CoolPathResponse:
    if not store._initialized:
        store.initialize()

    try:
        response = router_engine.calculate_routes(
            orig_lat=payload.origin.lat,
            orig_lon=payload.origin.lon,
            dest_lat=payload.destination.lat,
            dest_lon=payload.destination.lon,
            departure_hour=payload.departure_hour,
            max_detour=payload.max_detour_factor,
            profile=payload.vulnerability_profile.value
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cool path routing computation error: {str(e)}"
        )


# ---------------------------------------------------------
# 7. POST /api/simulate/scenario
# ---------------------------------------------------------

@router.post(
    "/simulate/scenario",
    response_model=ScenarioSimulateResponse,
    summary="Dynamic Climate Scenario & Grid Blackout Simulation",
    description="Stress-tests city resilience under +2°C climate surge, +4°C heat dome, cascading electrical blackout, or aggressive greening initiatives."
)
async def post_simulate_scenario(payload: ScenarioSimulateRequest) -> ScenarioSimulateResponse:
    if not store._initialized:
        store.initialize()

    try:
        response = simulate_heat_scenario(
            scenario_type=payload.scenario_type,
            temp_delta_c=payload.temperature_delta_c,
            grid_power_available_pct=payload.grid_power_available_pct,
            vegetation_inc_pct=payload.vegetation_increase_pct,
            cool_roof_adoption_pct=payload.cool_roof_adoption_pct,
            target_ward_ids=payload.target_ward_ids
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario simulation error: {str(e)}"
        )


# ---------------------------------------------------------
# 8. GET /api/public/advice
# ---------------------------------------------------------

@router.get(
    "/public/advice",
    response_model=PublicAdviceResponse,
    summary="Public Heat Advisory & Nearest Relief Havens",
    description="GPS-tailored public safety advisory returning nearest active AC cooling centers, chilled hydration kiosks, and medical precautions."
)
async def get_public_heat_advice(
    lat: float = Query(23.0225, ge=-90.0, le=90.0, description="Current latitude coordinate"),
    lon: float = Query(72.5714, ge=-180.0, le=180.0, description="Current longitude coordinate"),
    age_group: str = Query("adult", description="'child', 'adult', or 'elderly'"),
    activity: str = Query("commuter", description="'indoor', 'commuter', 'outdoor_laborer'"),
    has_preexisting_conditions: bool = Query(False, description="Flag for cardiovascular or respiratory conditions")
) -> PublicAdviceResponse:
    if not store._initialized:
        store.initialize()

    try:
        response = generate_public_advice(
            lat=lat,
            lon=lon,
            age_group=age_group,
            activity=activity,
            has_conditions=has_preexisting_conditions
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Public advisory lookup failed: {str(e)}"
        )


# ---------------------------------------------------------
# 9. Additional Relief Infrastructure Endpoints
# ---------------------------------------------------------

@router.get(
    "/cooling-centers",
    response_model=List[CoolingCenterItem],
    summary="List All Active Cooling Centers",
    description="Directory of designated municipal air-conditioned community shelters, libraries, and underground cooling havens."
)
async def get_cooling_centers(
    ward_id: Optional[str] = Query(None, description="Optional filter by ward ID")
):
    if not store._initialized:
        store.initialize()

    results = []
    for c in store.cooling_centers:
        if ward_id and c["ward_id"] != ward_id.upper():
            continue
        results.append(CoolingCenterItem(
            center_id=c["center_id"],
            name=c["name"],
            facility_type=c["facility_type"],
            address=c["address"],
            coordinates=Coordinates(**c["coordinates"]),
            distance_meters=0.0,
            walking_time_minutes=0,
            operating_hours=c["operating_hours"],
            capacity_persons=c["capacity_persons"],
            has_medical_staff=c["has_medical_staff"],
            phone_contact=c["phone_contact"]
        ))
    return results


@router.get(
    "/hydration-points",
    response_model=List[HydrationPointItem],
    summary="List All Free Hydration & Water Kiosks",
    description="Directory of chilled drinking water ATMs, temple piaus, and public hydration posts."
)
async def get_hydration_points(
    ward_id: Optional[str] = Query(None, description="Optional filter by ward ID")
):
    if not store._initialized:
        store.initialize()

    results = []
    for h in store.hydration_points:
        if ward_id and h["ward_id"] != ward_id.upper():
            continue
        results.append(HydrationPointItem(
            point_id=h["point_id"],
            name=h["name"],
            water_source_type=h["water_source_type"],
            coordinates=Coordinates(**h["coordinates"]),
            distance_meters=0.0,
            status=h["status"],
            is_free=h["is_free"]
        ))
    return results
