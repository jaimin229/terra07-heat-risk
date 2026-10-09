# 07 — Validation, Tests, Honest Limitations

## Unit tests (`pytest`, must pass in CI-style run `make test`)
- `grid`: cells tile the bbox, no overlaps, areas ≈ grid_size².
- `landsat scaling`: known DN → known °C (e.g. DN 44,000 → 44,000×0.00341802+149 = 299.39 K → 26.2 °C; assert).
- `cloud mask`: synthetic QA values with each bit set are masked.
- `normalisation`: winsorise + min–max stays in [0,1]; constant column handled.
- `scoring`: contributions sum to Risk (tolerance 1e-9); component weights sum to 1; missing-indicator re-normalisation works.
- `explain`: sentence numbers equal underlying data.
- `hotspots`: on a hand-built grid with an obvious hot block, Gi* flags it.
- `actions`: adding a facility never increases risk; greedy marginal gains non-increasing; budget plan never exceeds budget; no double counting of a cell.
- `no-fake-data`: grep `app/` and `heatlens/` for `np.random`, `random.` outside `tests/` and `heatlens/testing/fixtures.py`.
- Synthetic fixtures live ONLY in `heatlens/testing/fixtures.py` and are used only by tests.

## Data validation (run in pipeline; results written to `reports/validation.json` and shown on the Method page)
1. **Physical sanity:** Spearman(LST, NDVI) < 0; Spearman(LST, building_coverage) > 0; report values.
2. **Temporal consistency:** split scenes randomly into two halves (seeded), compute LST composites separately, report Spearman rank correlation of cell LST between halves (expect high, > 0.8). Shows the pattern is stable, not one-day noise.
3. **Cross-sensor check:** compare cell-level LST ranking with MODIS MOD11A1 (1 km, via Planetary Computer `modis-11A1-061`) aggregated to the same period at coarse scale; report correlation honestly (resolution differs).
4. **Air-temperature context:** compare the hot-season LST city mean against Open-Meteo archive daily max for the same dates; report the offset (surface vs air, expected not equal).
5. **Known-hot-places check:** list the top-10 clusters by name; the team inspects them against local knowledge (dense markets, old-city lanes, industrial belts vs riverfront/parks) and records the qualitative result. Cold spots should include parks/water-adjacent greens.
6. **Sensitivity:** results of the Monte-Carlo analysis from 03 §7.
7. **Population control total** check from 02 §3.

## Limitations (must appear in app + report)
- Landsat morning-overpass LST, 30 m (thermal natively 100 m), clear-sky composite biased to cloud-free days.
- Landsat thermal resolution is coarser than a single street; "street level" here means 250 m cells with 30 m underlying pixels, refinable to street segments by aggregating to OSM road buffers (optional stretch: compute risk per road segment buffer of 30 m).
- No indoor/housing-quality, income, air-conditioning access, or occupation microdata — proxies used where stated.
- OSM incompleteness; WorldPop modelled 2020 population; costs are assumptions; cooling effect is correlational.
- Relative score, not an absolute health threshold.
- Not validated against heat-illness case data (no public street-level data available); recommend integrating hospital/ambulance heat-illness records if the city shares them.

## Optional stretch (only after everything above works)
- Street-segment risk (30 m buffer around OSM roads, average of cell scores weighted by overlap) shown as coloured lines — directly "which streets".
- Ward-level aggregation if OSM boundaries exist.
- Time-of-day sensitivity using ECOSTRESS? (only if data is accessible without login; otherwise skip).
