# 01 — Project Spec

## Name
**HeatLens** — street-level heat-risk mapping and action prioritisation. (Team TERRA07)

## Problem (from the hackathon)
City-wide temperature forecasts hide that dense, paved, shade-poor neighbourhoods with many elderly people and outdoor workers suffer far more. Build a platform that maps heat risk at neighbourhood/street level by combining temperature, surface and vulnerability data, and tells planners where to act first.

## What the finished product does
1. Computes a **0–100 heat-risk score for every 250 m grid cell** of a sample city area (optionally also aggregated to wards/neighbourhoods when boundaries are available).
2. Shows an interactive **map** with layers: Risk score, Land-surface temperature, Green cover, Building density, Elderly/children density, Hotspots (statistically significant clusters), Existing cooling centres and water points.
3. For any clicked cell, **explains exactly what drives its score** (per-indicator contribution chart + plain-language sentence).
4. Produces a **ranked list of priority areas** (CSV + table + map).
5. Produces **ranked actions**: where to plant shade, where to add drinking-water points, where to open/designate cooling centres — ranked by estimated risk reduction per rupee, with transparent assumptions.
6. **Planner dashboard** (weights sliders, budget slider, exports) and a simple **Public heat-advice view** (live weather category + local risk tier + nearest water/cooling centre + advice in English/Hindi/Gujarati).

## Sample area (default)
Ahmedabad, India — dense walled-city and riverfront core plus surrounding wards. Default bounding box in `config.yaml`:
`bbox: [72.54, 22.99, 72.62, 23.06]` (west, south, east, north), roughly 8 km × 8 km → ~1,000 cells at 250 m.
The code must work for ANY city by changing only `config.yaml` (bbox, season, name). Verify the bbox visually on first run and adjust if it clips the city badly.
Hot season window: April–June (pre-monsoon), last 3 years.

## Tech stack (fixed — do not substitute)
- Python 3.11
- Data: `geopandas`, `shapely`, `rasterio`, `rioxarray`, `xarray`, `odc-stac`, `pystac-client`, `planetary-computer`, `osmnx`, `overturemaps`, `requests`, `numpy`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`
- Spatial stats: `libpysal`, `esda`
- Network analysis: `osmnx`, `networkx`
- App: `streamlit`, `streamlit-folium`, `folium` (Leaflet), `plotly`
- Tests: `pytest`
- No API keys required for anything (Planetary Computer works anonymously via signed URLs; Open-Meteo is keyless). If a key-based source is added, it must be optional.

## Repo layout
```
terra07-heat-risk/
├── README.md                  # quick start, screenshots, architecture image
├── Makefile                   # make setup | data | score | actions | app | test | all
├── config.yaml                # ALL parameters (bbox, weights, costs, thresholds)
├── requirements.txt
├── docs/                      # these md files
├── heatlens/
│   ├── __init__.py
│   ├── config.py              # load/validate config.yaml (pydantic or dataclass)
│   ├── grid.py                # build 250 m grid in local UTM CRS
│   ├── ingest/
│   │   ├── landsat.py         # LST, NDVI, NDBI from Planetary Computer
│   │   ├── buildings.py       # Overture (fallback OSM) building coverage
│   │   ├── population.py      # WorldPop total + age groups
│   │   ├── osm.py             # amenities, landuse, walk network
│   │   └── weather.py         # Open-Meteo forecast + history
│   ├── features.py            # aggregate everything to grid → features.parquet
│   ├── scoring.py             # normalise, weighted sum, contributions
│   ├── hotspots.py            # Getis-Ord Gi*, priority classes
│   ├── sensitivity.py         # Monte-Carlo weight perturbation
│   ├── actions/
│   │   ├── cooling_model.py   # city-fitted LST ~ NDVI model + bootstrap CI
│   │   ├── shade.py
│   │   ├── water.py
│   │   ├── cooling_centres.py
│   │   └── rank.py            # unify + rank by benefit/cost
│   ├── explain.py             # plain-language driver sentences
│   └── provenance.py          # writes data_sources.json
├── app/
│   ├── streamlit_app.py       # entry
│   ├── pages/1_Planner_Dashboard.py
│   ├── pages/2_Public_Heat_Advice.py
│   ├── pages/3_Method_and_Data.py
│   ├── i18n.yaml              # EN / HI / GU strings
│   └── components/            # map.py, charts.py
├── data/
│   ├── raw/                   # gitignored (large rasters)
│   ├── cache/                 # gitignored
│   └── processed/             # COMMITTED: features.parquet, scores.geojson, actions.csv, provenance.json
├── reports/                   # figures, report.md → report.pdf
├── tests/
└── scripts/run_pipeline.py    # runs ingest → features → score → hotspots → actions
```

## config.yaml (create exactly this structure; values are defaults)
```yaml
city: Ahmedabad
bbox: [72.54, 22.99, 72.62, 23.06]
grid_size_m: 250
season: {months: [4, 5, 6], years: [2023, 2024, 2025]}
landsat: {max_cloud_cover: 15, min_scenes: 4}
weights:
  components: {hazard: 0.35, exposure: 0.25, vulnerability: 0.25, adaptive_gap: 0.15}
  hazard: {lst: 0.60, building_coverage: 0.20, veg_deficit: 0.20}
  exposure: {pop_density: 0.60, outdoor_activity_proxy: 0.40}
  vulnerability: {elderly_share: 0.60, child_share: 0.40}
  adaptive_gap: {dist_cooling_centre: 0.50, dist_water_point: 0.50}
normalisation: {winsor_low: 0.02, winsor_high: 0.98}
access: {water_walk_m: 300, cooling_walk_m: 1000}
tiers: {low: 25, moderate: 50, high: 75}   # score cut-offs → Low/Moderate/High/Extreme
actions:
  shade: {delta_ndvi: 0.10, max_plantable_fraction: 0.30, cost_inr_per_cell_per_0p1_ndvi: 1500000}
  water: {k: 15, cost_inr_per_point: 250000}
  cooling: {k: 8, cost_inr_per_centre: 1200000}
random_seed: 42
```
The cost numbers are **placeholder planning assumptions**; the app must label them "editable planning assumptions" and expose them in the sidebar. Do not present them as real quotes.
