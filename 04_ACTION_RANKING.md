# 04 — Actions Ranked by Impact (shade, water points, cooling centres)

Goal: a single ranked list of concrete interventions, each with a location, who benefits, estimated risk reduction, cost and benefit-per-cost — computed by **re-running the real scoring model under the intervention** (counterfactual), not by guessing.

## Common impact metric
`impact = Σ_cells pop_total_i × (Risk_before_i − Risk_after_i) / 1000` → **person-risk points averted**.
Optional vulnerable-weighted version: weight people by `1 + 2·elderly_share` (config) — expose as a toggle.
`benefit_cost = impact / cost_inr × 1e6` (points per ₹ million).
Costs come from `config.yaml` and are **editable planning assumptions**; label them so.

## A. Shade / urban greening (`actions/shade.py`, `actions/cooling_model.py`)
1. **Fit the city's own cooling relationship** (cell level, OLS with robust SE via `statsmodels`):
   `lst_mean_c ~ ndvi_mean + building_coverage + open_space_frac` (+ optional distance-to-water-body control). Report coefficients, R², and **bootstrap 95% CI (1,000 resamples) for the NDVI coefficient** β_ndvi (expected negative).
   - This is correlational, not causal. State that. Cross-check β_ndvi's magnitude against published urban-greening cooling ranges and show the comparison in the report (cite sources you actually found; don't invent citations).
2. **Intervention:** for each cell, plantable fraction `p_i = min(max_plantable_fraction, open_space_frac)`; ΔNDVI_i = `delta_ndvi × p_i / max_plantable_fraction` (scaled by how much space exists).
3. `LST_after_i = LST_i + β_ndvi × ΔNDVI_i` (use the **lower-bound** of the CI as the conservative case; also show central estimate). Also lower `veg_deficit` accordingly and **recompute the full risk score** with the same normalisation bounds as the baseline (freeze lo/hi from the baseline run so scores are comparable).
4. Cost_i = `cost_inr_per_cell_per_0p1_ndvi × (ΔNDVI_i / 0.1)`.
5. Output per cell: `shade_impact`, `shade_cost`, `shade_bc`, `delta_lst_c` (with CI). Rank cells; recommendation = "Plant/shade here, cooling ≈ X °C (CI a–b)". Minimum-effect floor: ignore cells with ΔLST < 0.1 °C.

## B. Drinking-water points (`actions/water.py`)
- **Demand weight per cell:** `d_i = pop_total_i × (1 + outdoor_activity_proxy_i) × (1 + 2·elderly_share_i)`.
- **Candidate sites:** OSM walk-network nodes within the AOI that are on pedestrian-accessible streets, thinned to ≥150 m spacing; prefer nodes near marketplaces/bus stops/transit/junctions (bonus tag only, no hand-tuning of results).
- **Coverage:** a cell is covered if walking distance from its centroid to a water point ≤ `access.water_walk_m` (300 m). Existing water points already cover some cells.
- **Greedy maximum coverage:** repeatedly pick the candidate that covers the largest not-yet-covered demand, k = `actions.water.k`. (Greedy gives ≥ (1 − 1/e) ≈ 63% of the optimum for this submodular objective — state it.) The greedy order = the rank.
- **Risk effect:** covered cells have `dist_water_m` updated to the new walking distance → recompute `A` → recompute Risk → impact via the common metric. Marginal impact per pick is recorded (diminishing returns curve plotted).
- Output: rank, lat/lon, nearest street name (OSM), cells covered, people newly covered, impact, cost, benefit-cost.

## C. Cooling centres (`actions/cooling_centres.py`)
- **Candidates:** OSM facilities flagged `candidate` (schools, community halls, places of worship marked `medium`, plus any `high` types not currently counted). Choosing existing public buildings = realistic and cheap (no new construction).
- **Coverage:** walking distance ≤ `access.cooling_walk_m` (1,000 m) from the cell centroid.
- **Demand weight:** `pop_65plus + pop_u5 + 0.3 × pop_total × outdoor_activity_proxy` (documented; configurable), further multiplied by cell hazard `H_i` so we prioritise places that are actually hot.
- Same greedy max-coverage, k = `actions.cooling.k`; record marginal gains; recompute `A` → Risk → impact.
- Output like water points, plus facility name/type/confidence.

## D. Unified ranked action list (`actions/rank.py`)
- Concatenate A, B, C outputs into one table: `action_type, rank_within_type, target (cell_id/facility), lat, lon, people_benefited, impact, cost_inr, benefit_cost, rationale, evidence_cell_drivers`.
- **Global ranking by benefit_cost** (cheap high-impact first) AND an alternative **budget-constrained plan**: given a budget slider B (₹), pick actions by benefit-cost until B is exhausted, no double counting (interventions in the same cell are applied jointly — re-score after each applied intervention to account for overlap; implement by sequentially applying and recomputing marginal impact).
- Show the cumulative curve "risk points averted vs budget".
- Each action must carry a human-readable `rationale` built from real values: "Covers 4,120 people incl. 310 aged 65+; nearest water point is currently 1.2 km away."

## E. Honesty requirements
- Cooling estimates carry confidence intervals; costs are labelled assumptions.
- The ranking is a **decision-support prioritisation**, not an engineering design; recommend ground-truthing (site visits) before implementation — state this in the UI.
- Results are reproducible given the config and seed. Unit-test: adding a water point can never *increase* a cell's risk; impact is monotone non-negative; greedy marginal gains are non-increasing.
