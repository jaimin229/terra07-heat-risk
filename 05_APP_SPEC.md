# 05 — App Spec (Streamlit + Leaflet via folium)

Entry: `app/streamlit_app.py` (landing/overview) + multipage `pages/`. App reads ONLY from `data/processed/` (precomputed) except lightweight recomputation (weight sliders, budget slider) done in-memory with numpy in < 1 s. Use `st.cache_data`. App must start with `streamlit run app/streamlit_app.py` offline.

If `provenance.json` marks data as synthetic → full-width red banner "SYNTHETIC DATA — NOT FOR DECISIONS".

## Landing (streamlit_app.py)
- Title HeatLens · TERRA07, one-paragraph problem statement, 4 headline metrics computed from data: number of cells, population in High/Extreme cells, % of 65+ residents in High/Extreme cells, number of robust hotspots.
- Data freshness line (Landsat date range, weather fetch time).
- Links to the two views.

## Page 1 — Planner Dashboard
**Sidebar:** layer selector (Risk score · LST · Green cover (NDVI) · Building density · Population density · Elderly share · Hotspots (Gi*) · Hot & vulnerable class · Access gap), basemap toggle (CartoDB light / OSM / satellite via Esri World Imagery tile), tier filter, "robust hotspots only" checkbox, weight sliders (4 components + indicator sliders in an expander; auto-normalise; a "Reset to default" button), planning-assumption inputs (costs, k, budget).
**Main (tabs):**
1. **Map** — folium map, cells as GeoJSON polygons coloured by the chosen layer with legend; tooltip (cell id, score, tier, population); existing water points and cooling centres as toggleable marker layers (clustered); recommended actions as distinct icons (tree / drop / snowflake) when the Actions overlay is on. Click a cell → right panel.
2. **Why this score?** — for the selected cell: score gauge, tier, component bars, **waterfall/stacked bar of indicator contributions vs area median** (plotly), the generated plain-language explanation, raw values table (LST °C, NDVI, building %, people, 65+, <5, walk to water/cooling), robust-hotspot badge and rank interval from sensitivity.
3. **Priority areas** — two ranked tables (by risk; by people-weighted risk) with filters, cluster names, download CSV; mini-map highlighting the top-N.
4. **Actions** — unified ranked action table; budget slider → recommended package, KPI cards (people benefited, risk points averted, % reduction in High/Extreme population), cumulative-benefit curve, map overlay; before/after risk map toggle; download CSV/GeoJSON.
5. **Robustness** — rank-interval chart for top 30 cells, top-decile stability histogram, scenario comparison (default weights vs your weights: Spearman and top-decile overlap).
6. **Export** — GeoJSON of scores, CSV of priorities & actions, and a "one-page brief" generated as Markdown/PDF for the selected cluster (real values only).
**Performance:** ≤ 3,000 cells renders smoothly; simplify geometry (cells are squares so just reproject to EPSG:4326).

## Page 2 — Public Heat Advice (simple)
- Big, readable, mobile-friendly. Language switch EN / हिन्दी / ગુજરાતી (strings in `i18n.yaml`; mark Hindi/Gujarati as "machine-drafted, to be reviewed by a native speaker" in the README).
- Input: "Use map click" (small map) or pick area from a dropdown of named clusters/neighbourhoods; optional lat/lon field.
- Output card: today's forecast max/apparent temperature (Open-Meteo) → heat category (see 02 §5) → **your area's heat-risk tier** → 3–5 plain advice lines tailored to the tier and category (hydrate, avoid 12–4 pm outdoor work, check on elderly neighbours, wear light clothing, heatstroke warning signs and "call local emergency number (112 in India)") → **nearest water point and cooling centre with walking distance and an OSM/Google Maps directions link** (real data from the nearest facility, or "none mapped within 1.5 km — data may be incomplete").
- 7-day mini forecast strip with category colours.
- Medical safety: advice limited to widely published public-health guidance (e.g. NDMA/IMD heat-action guidance, WHO); link those sources; state "not medical advice".

## Page 3 — Method & Data
Renders the content of docs 02/03 in short form: formula (LaTeX), weights table (live from config), data-source table (from provenance.json with dates/licences), assumptions & limitations list, validation results (from the tests/validation output), architecture diagram image.

## UX rules
- Colour scale: perceptually uniform, colour-blind safe (e.g. YlOrRd for risk, viridis for LST, YlGn for NDVI). Never rely on colour alone (tier labels in tooltips/tables).
- Every chart/map has title, units, source line.
- Empty/error states are explicit (no data, API down).
- No lorem ipsum, no hard-coded demo values anywhere in `app/`. Add a test that greps the app code for suspicious literals (e.g. `random`, `np.random`) and fails if found.
