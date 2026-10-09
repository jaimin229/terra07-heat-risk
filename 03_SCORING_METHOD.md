# 03 — Heat-Risk Scoring Method

Follows the IPCC risk framing: **risk = hazard × exposure × vulnerability**, with a lack of coping capacity increasing risk. For transparency and exact explainability we use a **weighted additive composite index** (standard in vulnerability-index practice, e.g. heat-vulnerability indices in the literature) instead of a black-box model.

## 1. Indicators (all per 250 m cell)
| Component | Indicator | Direction (higher = riskier) | Source |
|---|---|---|---|
| Hazard (H) | `lst_mean_c` land-surface temperature | + | Landsat |
| Hazard (H) | `building_coverage` | + | Overture/OSM |
| Hazard (H) | `veg_deficit = 1 − clip(ndvi_mean, 0, 1)` | + | Landsat |
| Exposure (E) | `pop_density` | + | WorldPop |
| Exposure (E) | `outdoor_activity_proxy` | + | OSM (proxy) |
| Vulnerability (V) | `elderly_share` (65+) | + | WorldPop |
| Vulnerability (V) | `child_share` (<5) | + | WorldPop |
| Adaptive-capacity gap (A) | `dist_cooling_m` | + | OSM + network |
| Adaptive-capacity gap (A) | `dist_water_m` | + | OSM + network |

## 2. Normalisation
For each indicator x: winsorise at the 2nd/98th percentiles (config), then min–max to [0,1]: `z = (x_w − lo)/(hi − lo)`. Skewed variables (`pop_density`, distances) use `log1p` before winsorising. Missing values: indicator excluded for that cell and the remaining weights within the component re-normalised; the cell is flagged `partial_data`. Cells with no valid LST are not scored (shown grey).
Normalisation is **relative to the study area** — a score of 90 means "among the worst in this city area", not an absolute physiological threshold. State this.

## 3. Aggregation
Component score = weighted mean of its indicators (weights in config, sum to 1 per component).
`Risk = 100 × (w_H·H + w_E·E + w_V·V + w_A·A)` with default `0.35/0.25/0.25/0.15`.
Tiers: Low (<25), Moderate (25–50), High (50–75), Extreme (≥75), from config.

## 4. Exact explanation (`explain.py`)
Because the score is linear, indicator contribution is exact:
`contribution_k = 100 × w_component × w_indicator_in_component × z_k`  → sums to the Risk score.
Store one column per indicator (`c_lst`, `c_building`, …) and the component totals.
Also compute **contribution relative to the area median** (`c_k − median(c_k)`): the "why is this cell worse than typical" view — this is what the waterfall chart shows.
Generate a plain-language sentence from templates, e.g.:
> "Cell r12_c07 scores 82 (Extreme). Biggest drivers: surface 6.1 °C hotter than the area median (+14 pts), 71 % built-up (+11 pts), and 1.4 km walk to the nearest cooling centre (+9 pts). Protective: none."
Numbers in the sentence must be computed, never hand-typed. Unit-test the sentence generator.

## 5. Hotspots and priority classes (`hotspots.py`)
- **Getis-Ord Gi\*** on the Risk score with queen-contiguity weights (`libpysal.weights.Queen`), 999 permutations, report z and p. Hotspot = z > 1.96 & p < 0.05 (also 99% class). Cold spot analog.
- **Bivariate priority class:** "Hot & vulnerable" = `H` in top quartile AND `V` in top quartile (population-weighted logic: also require pop_total ≥ the 25th percentile so empty land isn't flagged). This directly answers "which streets and people".
- **Population at risk:** `pop_65plus` and `pop_total` summed over Extreme+High cells.

## 6. Priority-area ranking (deliverable)
Keep two clearly separate rankings so nothing is hidden:
1. **By risk score** (where conditions are worst).
2. **By people-weighted risk** = `Risk × pop_total / 1000` ("person-risk points": where the most people suffer).
Export both to `data/processed/priority_areas.csv` with columns: rank, cell_id, lat, lon, risk, tier, hotspot_class, pop_total, pop_65plus, top_3_drivers, nearest_water_m, nearest_cooling_m. Group adjacent top cells into **clusters** (connected components of top-decile cells) and give each cluster a readable name (nearest OSM road/suburb/landmark via the cluster centroid).

## 7. Sensitivity & robustness (`sensitivity.py`) — required, shows rigor
- Monte-Carlo: 1,000 draws of component weights from a Dirichlet centred on the defaults (concentration 20) and indicator-within-component weights likewise; recompute scores.
- Report per cell: median rank, 5–95% rank interval; **top-decile stability** = fraction of draws in which a cell stays in the top decile.
- Report global: mean Spearman between default and perturbed rankings; % of default top-decile cells that stay top-decile in ≥ 80% of draws.
- Alternative aggregation check: recompute using geometric mean of (H,E,V,A) and report rank correlation with the additive version.
- Show a "robust hotspot" badge in the app for cells with stability ≥ 0.8.

## 8. Assumptions to list in the report (verbatim honest list)
1. Equal ranking of hazard sources is a modelling choice; weights are editable and sensitivity-tested.
2. LST ≠ air temperature; morning-overpass surface temperature is a relative indicator.
3. Age structure is modelled (WorldPop 2020), not census.
4. Outdoor-worker exposure is a land-use-based proxy.
5. Facility data are from OSM and incomplete; access gaps may be overstated where facilities are untagged.
6. Scores are relative within the study area.
