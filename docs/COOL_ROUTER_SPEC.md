# TERRA07: Cool-Corridor Navigation & Street Routing Engine

> **Module**: `engine/cool_router.py`  
> **Team**: TERRA07 (Software Track: Heat-Risk Mapping at Human Scale)  
> **Role**: Agent 6 (Safe Cool-Corridor Navigation & Street Routing Engineer)

---

## 1. Overview & Objective

During extreme urban heat events, pedestrians, vulnerable citizens, and outdoor workers experience severe thermal strain when forced along asphalt-paved, unshaded arterial corridors. 

The **Cool-Corridor Navigation Engine** calculates human-scale safe walking paths that minimize cumulative solar thermal exposure while prioritizing mature tree canopy cover and public hydration infrastructure (smart misting stations, chilled water refill points).

---

## 2. Mathematical Formulation & Thermal Exposure Cost Function

Standard navigation engines compute the shortest path by minimizing pure physical distance:
$$\min \sum_{e \in \mathcal{P}} \text{Length}(e)$$

The **Cool-Corridor Routing Engine** computes paths through a multi-factor thermal impedance cost function:

$$\text{Cost}(e) = \text{Length}(e) \times \left(1 + \alpha \cdot \frac{\text{HeatRisk}(e)}{100} - \beta \cdot \text{ShadeRatio}(e) - \text{Bonus}_{\text{water}}(e)\right)$$

Where:
- $\text{Length}(e)$: Physical length of street segment in meters.
- $\text{HeatRisk}(e) \in [0, 100]$: Urban Heat Island / surface temperature heat risk score.
- $\alpha \ge 0$: Heat risk sensitivity penalty multiplier (default $= 2.0$).
- $\text{ShadeRatio}(e) \in [0.0, 1.0]$: Tree canopy shade ratio shielding direct solar irradiance.
- $\beta \ge 0$: Canopy cooling benefit multiplier (default $= 1.2$).
- $\text{Bonus}_{\text{water}}(e)$: Thermal relief discount for passing hydration kiosks or misting stations (default $= 0.25$ per kiosk, capped at $0.6$).
- $\text{CostMultiplier}_{\text{min}}$: Non-negative floor ($0.15$) ensuring positive weights for Dijkstra/A* routing.

### Net Human Thermal Strain Formulation
Direct solar irradiance transfers massive radiative thermal load ($T_{\text{mrt}}$, Mean Radiant Temperature). Tree canopies block approximately $70\%$ of direct radiative load:
$$\text{Net Thermal Strain}(\mathcal{P}) = \sum_{e \in \mathcal{P}} \text{Length}(e) \times \text{HeatRisk}(e) \times (1 - 0.70 \times \text{ShadeRatio}(e))$$

---

## 3. NetworkX Graph Schema

### Nodes (Intersections & Pedestrian Waypoints)
```python
router.add_intersection(
    node_id="I_0_0",
    lat=37.7749,
    lon=-122.4194,
    name="5th Ave & Market St",
    has_hydration_kiosk=True,
    kiosk_description="Smart Misting Station & Refill Fountain"
)
```

### Edges (Street Segments)
```python
router.add_street_segment(
    u="I_0_0",
    v="I_0_1",
    street_name="Emerald Tree Boulevard",
    length_m=120.0,          # Auto-calculated via Haversine if omitted
    heat_risk=32.0,          # 0 (cool) to 100 (extreme hazard)
    canopy_shade_ratio=0.85, # 85% tree canopy coverage
    hydration_points=1,      # Mid-block hydration stations
    bidirectional=True
)
```

---

## 4. Key Routing Capabilities

1. **Standard Shortest Path (`find_shortest_path`)**: Minimizes pure metric distance.
2. **Cool-Corridor Path (`find_cool_path`)**: Minimizes thermal impedance and prioritizes tree-lined shaded corridors and hydration stations.
3. **Balanced Path (`find_balanced_path`)**: Constrains walking detour to a maximum ratio (e.g. $\le 1.25 \times$ shortest distance) while maximizing cooling relief.
4. **Route Comparison (`route_and_compare`)**: Computes comprehensive comparative metrics between shortest and cool paths.
5. **Turn-by-Turn Directions with Thermal Alerts**: Step-by-step instructions annotated with canopy shade percentage, water kiosk proximity alerts, and thermal danger levels.
6. **GeoJSON Import & Export**: Full interoperability with GeoJSON LineStrings and Points for map rendering in Leaflet and Mapbox.

---

## 5. Comparative Metrics & Turn Alerts Example

### Route Comparison Summary
```markdown
### 🌿 Cool-Corridor Walking Path Comparison

- **Distance**: 480m (Shortest) ➔ 720m (Cool) (+240m, +3.1 mins walk)
- **Average Heat Risk**: 87.6 (Extreme) ➔ 42.3 (Moderate) ([51.7% risk reduction])
- **Canopy Shade Cover**: 7.5% ➔ 82.0% (+74.5% shade gain)
- **Hydration Kiosks Encountered**: 0 ➔ 3 (+3 water access points)
- **Net Human Thermal Strain Reduction**: 68.2%
```

### Step-by-Step Navigation with Thermal Safety Alerts
```text
Step 1: Head on Emerald Tree Boulevard (240m) - 🌿 85% canopy shade, Water Kiosk at ~160m [Cool Shaded Corridor]
Step 2: Turn right onto Parkside Way (300m) - 🌿 82% canopy shade, Water Kiosk at ~210m [Cool Shaded Corridor]
Step 3: Continue on Maple Avenue 4 (150m) - 52% partially shaded
Step 4: Arrive at Ave 5 & St 5. [🏁 Safe arrival at destination.]
```

---

## 6. Python API Quickstart

```python
from engine.cool_router import CoolRouter

# 1. Create router (or load from GeoJSON)
router = CoolRouter.create_synthetic_urban_grid(rows=5, cols=5, block_size_m=120.0)

# 2. Compute comparison between origin and destination
comparison = router.route_and_compare("I_0_0", "I_4_4")

# 3. Access structured results for REST API or frontend
data = comparison.to_dict()
geojson_route = comparison.cool_path.to_geojson()

# 4. Print summary
print(comparison.summary_markdown())
```

---

## 7. Test Coverage

Comprehensive unit tests are located in `tests/test_cool_router.py`:
- `TestSpatialHelpers`: Haversine calculation, compass bearings, turn direction classification, heat index categorization.
- `TestGraphConstruction`: Node/edge additions, auto-distance, input clamping, exception safety.
- `TestCostFunction`: Alpha/beta sensitivities, hydration discount bonuses, non-negativity guarantees.
- `TestRoutingAndComparisons`: Shortest vs cool routing divergence on diamond test networks, metric percentage calculations, markdown generation.
- `TestTurnByTurnDirections`: Step numbering, street name consolidation, thermal alert triggering.
- `TestBalancedRouting`: Bounded detour constraint verification.
- `TestSyntheticGridAndGeoJSON`: Full GeoJSON roundtrip export, import, and route execution.

All tests pass cleanly (`pytest tests/test_cool_router.py`).
