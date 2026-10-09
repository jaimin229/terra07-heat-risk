# 02 — Real Data Pipeline

All data below is free and public. Build each ingest module so it (a) caches raw downloads in `data/cache/`, (b) retries on network errors, (c) logs what it fetched, and (d) records provenance in `data/processed/provenance.json` (dataset, URL/collection, date range, scene IDs, resolution, licence, fetch timestamp).

**If a URL below has changed, search for the current one — do NOT substitute fake data. If a dataset truly cannot be obtained, stop, say so, and use the documented fallback.**

## 0. Grid (`grid.py`)
- Take bbox (EPSG:4326) → estimate UTM CRS with `GeoSeries.estimate_utm_crs()` (Ahmedabad → EPSG:32643).
- Build square cells of `grid_size_m`; give each `cell_id` (`r{row}_c{col}`), centroid lon/lat, area.
- Save `data/processed/grid.geoparquet`.

## 1. Land-surface temperature, vegetation, built-up index — Landsat 8/9 Collection 2 Level-2 (`ingest/landsat.py`)
- Source: Microsoft Planetary Computer STAC `https://planetarycomputer.microsoft.com/api/stac/v1`, collection `landsat-c2-l2`. Anonymous access works; use `planetary_computer.sign_inplace` as the `modifier` on the `pystac_client.Client`.
- Query: bbox, datetimes in the hot-season months for the configured years, `eo:cloud_cover < landsat.max_cloud_cover`, platforms `landsat-8` and `landsat-9`.
- Load with `odc.stac.load` at 30 m, CRS = local UTM, bands: `lwir11`, `red`, `nir08`, `swir16`, `qa_pixel`, `bbox` cropped.
- **Scaling (Collection 2 L2):**
  - Surface temperature: `K = lwir11 * 0.00341802 + 149.0`, `°C = K - 273.15`. (Prefer reading `raster:bands` scale/offset from the STAC item metadata and assert they match.)
  - Surface reflectance: `refl = DN * 0.0000275 - 0.2`.
- **Cloud mask** from `qa_pixel`: mask bits 1 (dilated cloud), 2 (cirrus), 3 (cloud), 4 (cloud shadow). Also drop nodata (DN == 0).
- **Indices:** `NDVI = (NIR - RED)/(NIR + RED)`, `NDBI = (SWIR1 - NIR)/(SWIR1 + NIR)`.
- **Compositing:** per-pixel **median** across clear observations. Require ≥ `landsat.min_scenes` valid scenes; otherwise widen years/cloud threshold and log it.
- **Daytime-overpass caveat:** Landsat passes ~10:45 local time; LST is a *relative* surface-heating signal, not the afternoon peak air temperature. State this in the app and report.
- Aggregate to grid with **zonal mean** (use `rasterio.features`/`rioxarray` + `exactextract` or a vectorised `groupby` on pixel→cell index). Also store `lst_p90` (90th percentile in cell) and `valid_pixel_frac`. Cells with `valid_pixel_frac < 0.5` get NaN and are flagged, never imputed silently.
- Save the composite rasters as GeoTIFF in `data/raw/` (gitignored) and small PNG previews to `reports/figures/`.

## 2. Buildings — Overture Maps (fallback OSM) (`ingest/buildings.py`)
- Primary: `overturemaps download --bbox=W,S,E,N -f geoparquet --type=building -o data/cache/buildings.parquet` (CLI from the `overturemaps` package; keyless).
- Fallback: `osmnx.features_from_bbox(..., tags={"building": True})`.
- Clip to cell polygons in UTM; compute `building_coverage = sum(footprint area ∩ cell) / cell area` (0–1), `building_count`.
- Log which source was used and the total footprint count. Building height is mostly missing → do NOT use height.

## 3. Population & age structure — WorldPop (`ingest/population.py`)
- Source: WorldPop (https://www.worldpop.org/), India, year 2020, constrained 100 m or 1 km age-sex structure GeoTIFFs plus total population.
- Download the per-age-group rasters (sex f and m; age groups 0, 1, 5, …, 80). The path pattern is under `https://data.worldpop.org/GIS/AgeSex_structures/...` — **verify the exact URL on the WorldPop site at build time** and fall back to the 1 km product if the 100 m constrained one is missing.
- Compute rasters: `pop_total`, `pop_65plus` = sum of groups 65, 70, 75, 80 (both sexes), `pop_u5` = sum of groups 0 and 1.
- Aggregate to grid by **sum** (people are additive; resample by area-weighted sum, not mean). Check: total over AOI should match raster total within 1%.
- Derive `pop_density` (people/km²), `elderly_share = pop_65plus / pop_total`, `child_share = pop_u5 / pop_total` (set NaN where pop_total < 20 and mask those from share-based scoring by shrinking toward the city mean: `share_adj = (pop_65plus + k·m) / (pop_total + k)` with k = 50, m = AOI mean share. Document this empirical-Bayes-style shrinkage.)
- Honesty note: WorldPop is a modelled estimate (2020) → show "modelled, not census" in the UI.

## 4. OSM features (`ingest/osm.py`) via `osmnx`
Query once for the bbox (with 1 km buffer so edge cells see nearby facilities):
- **Drinking water points:** `amenity=drinking_water`, `amenity=water_point`, `man_made=water_well` (with drinking use if tagged) — existing water points.
- **Cooling-centre candidates & existing centres:**
  - Existing/designated: `amenity=community_centre`, `amenity=library`, `amenity=townhall`, `amenity=hospital`, `amenity=clinic`, `shop=mall`, `amenity=place_of_worship` (large, as informal shelter, flagged lower confidence), `amenity=school` (candidate only; schools are closed in summer vacations → good candidates).
  - Tag each with `type` and `confidence` (`high` for hospital/community_centre/library/townhall/mall; `medium` for school/place_of_worship). Only `high` count as *existing* cooling provision; `medium` are *candidate sites* for action ranking.
- **Outdoor-activity proxy inputs:** counts/areas of `amenity=marketplace`, `highway=bus_stop`, `railway=station`, `public_transport=platform`, `landuse=construction|industrial|commercial|retail`, `shop=*` density on roads, `highway=pedestrian`. Aggregate per cell, normalise each by winsorised min–max, take a documented weighted mean (marketplace 0.3, construction/industrial 0.3, transit stops 0.2, shop density 0.2) → `outdoor_activity_proxy` (0–1).
  - **Label clearly as a PROXY** for outdoor workers / street vendors / commuters in the UI. Provide an optional override: if `data/user/outdoor_workers.csv` (cell_id or ward → value) exists, use it instead.
- **Walking network:** `osmnx.graph_from_bbox(network_type="walk")`, projected to UTM. Used for walking-distance access analysis.
- **Access distances:** for each cell centroid compute walking distance (metres) to nearest existing water point and nearest existing cooling centre (multi-source Dijkstra from facilities, snap centroid to nearest node; if the graph is disconnected, fall back to straight-line distance ×1.3 and flag). Store `dist_water_m`, `dist_cooling_m` (cap at 3000 m).
- OSM completeness in Indian cities is partial. Say so in the limitations. Never invent facilities.

## 5. Weather — Open-Meteo (`ingest/weather.py`, keyless)
- Forecast: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&daily=temperature_2m_max,apparent_temperature_max,relative_humidity_2m_mean&timezone=auto&forecast_days=7`
- Historical (for context/validation): `https://archive-api.open-meteo.com/v1/archive` for the same hot-season window.
- Cache with a timestamp; the public view shows "last updated" and degrades gracefully ("weather service unavailable") — never fake a temperature.
- **Heat category (public view)** uses IMD-style plains criteria: max temp ≥ 40 °C = heatwave conditions; ≥ 45 °C = severe heatwave; 37–39.9 °C = "very hot"; below 37 = "hot/normal". Verify against current IMD definitions during build and cite the IMD source in the Method page. Combine with local risk tier for personalised advice.

## 6. Ward / neighbourhood boundaries (optional layer)
- Try OSM `boundary=administrative` with `admin_level` 9/10 for the bbox (often wards/suburbs). If found, aggregate scores to those polygons population-weighted. If not found, skip; the grid is the primary unit. Never fabricate boundaries.

## 7. Output schema — `data/processed/features.parquet` (one row per cell)
`cell_id, geometry(UTM), lon, lat, lst_mean_c, lst_p90_c, ndvi_mean, ndbi_mean, valid_pixel_frac, building_coverage, building_count, pop_total, pop_65plus, pop_u5, pop_density, elderly_share, child_share, outdoor_activity_proxy, dist_water_m, dist_cooling_m, open_space_frac, flags (string list)`
- `open_space_frac = 1 − building_coverage − road_fraction` (road_fraction from OSM road polygons/buffers by highway class widths; clip ≥ 0). Used by the shade module as the plantable ceiling.

## 8. Acceptance checks for this phase (the AI must run and print them)
- Number of Landsat scenes used, date range, cloud filter; LST range sanity (expect roughly 30–55 °C surface temps in Apr–Jun daytime; flag if outside 20–65).
- Total population in AOI vs WorldPop raster total (≤1% diff).
- % cells with valid LST; % with buildings > 0; count of water points and cooling centres found.
- Spearman(LST, NDVI) should be clearly **negative**; Spearman(LST, building_coverage) clearly **positive**. If not, investigate (cloud mask, scaling, CRS) before moving on.
- A preview PNG of each layer in `reports/figures/`.
