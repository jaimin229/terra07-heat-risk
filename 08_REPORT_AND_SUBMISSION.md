# 08 — Report, Deliverables Checklist, Demo Script, Judge Q&A

## Deliverables → where they live
| Required by the problem statement | File / feature |
|---|---|
| Heat-risk map for one sample city area | App Planner → Map; `reports/figures/risk_map.png`; `data/processed/scores.geojson` |
| Ranked list of priority areas | `data/processed/priority_areas.csv`; app tab "Priority areas" |
| Scoring method and assumptions | `docs/03_SCORING_METHOD.md`; app "Method & Data"; report §3 |
| Architecture diagram | `reports/figures/architecture.png`; `docs/06_ARCHITECTURE.md` |
| Code repository | GitHub repo with README, Makefile, tests (public, MIT licence) |
| Short report | `reports/report.pdf` (max 6 pages) |
| Key features: score per area, hotspot map, explanation, ranked actions, planner dashboard, public advice view | App pages 1–2 |

## Short report outline (`reports/report.md` → PDF via pandoc or weasyprint; AI writes with REAL numbers pulled from output files, via a script `scripts/make_report.py` that fills a template — no hand-typed stats)
1. **Problem & approach** (½ page)
2. **Study area & data** — table of sources, dates, resolution, licence (from provenance.json)
3. **Method** — indicators, normalisation, weights, formula, hotspot stats, sensitivity; assumptions list
4. **Results** — risk map, hotspot map, top-10 priority clusters with drivers, population at risk, example explanation for one cell
5. **Actions** — ranked table, budget plan, cooling-model result with CI
6. **Validation & limitations** — numbers from `validation.json`
7. **Architecture & reproducibility** — diagram, how to run
8. **Impact & next steps** — integrate ward data, hospital records, live sensor network, street-level mapping, multi-city rollout

## Demo script (3–4 minutes)
1. (20 s) "Heatwaves hit unevenly — one city forecast says 42 °C, but streets differ by many degrees and people differ by far more." Show landing metrics.
2. (45 s) Planner map: toggle LST → Risk → Hotspots. Point at the old-city cluster vs a green/riverfront area.
3. (45 s) Click a hotspot cell → "Why this score?" → read the sentence → show waterfall.
4. (45 s) Actions tab: set budget → ranked package; show before/after map and people benefited; mention CI on cooling.
5. (30 s) Public advice page in Hindi/Gujarati: real forecast today → category → nearest water point.
6. (30 s) Method page: data sources + robustness + limitations ("we tell you what we don't know").
7. (15 s) `make all` reproducibility + repo.

## Likely judge questions — honest answers
- **Is the data real?** Yes: Landsat 8/9 surface temperature (USGS/NASA via Planetary Computer), Overture/OSM, WorldPop, Open-Meteo. Provenance page lists scene dates.
- **Why not machine learning?** We have no street-level ground-truth heat-illness labels; an unsupervised-label ML model would fake precision. An auditable index with exact attribution + sensitivity analysis is the defensible choice. (ML is a next step once health outcome data exists.)
- **Is surface temp = how hot people feel?** No; it is a relative surface-heating signal. We pair it with building density, vegetation and exposure; air-temperature advice comes from the forecast.
- **How do you know the cooling numbers?** Fitted on this city's own data with bootstrap CIs, correlational, cross-checked with published ranges; shown as ranges, conservative bound used for ranking.
- **Can it scale to other cities?** Change bbox in `config.yaml`, run `make all`.
- **What about people we can't see (homeless, informal workers)?** Acknowledged as proxy limits; the platform accepts user-supplied ward/occupation data to replace proxies.
- **Costs?** Editable planning assumptions, not quotes.
