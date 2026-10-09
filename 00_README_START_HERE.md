# TERRA07 — Heat-Risk Mapping at Human Scale (AI Build Pack)

Agnitia Hackathon · Software Track · Team ID TERRA07

This pack is a set of instruction files for an AI coding agent (Claude Code, Cursor, Codex, etc.) to build the **complete, real, working** project. Nothing here is a mock-up: every number shown in the app must come from a real dataset or a documented, reproducible calculation.

## File order (give the AI ALL of them, in this order)
| # | File | Purpose |
|---|------|---------|
| 00 | 00_README_START_HERE.md | This index + non-negotiable rules |
| 01 | 01_PROJECT_SPEC.md | Goal, scope, sample area, repo layout, config |
| 02 | 02_DATA_PIPELINE.md | Exact real data sources, code approach, output schema |
| 03 | 03_SCORING_METHOD.md | Heat-risk formula, normalisation, explainability, hotspots, sensitivity |
| 04 | 04_ACTION_RANKING.md | Shade / water points / cooling centres ranked by impact |
| 05 | 05_APP_SPEC.md | Streamlit app: Planner dashboard + Public advice view |
| 06 | 06_ARCHITECTURE.md | Architecture diagram (Mermaid) + data flow |
| 07 | 07_VALIDATION_AND_TESTS.md | Tests, validation, honest limitations |
| 08 | 08_REPORT_AND_SUBMISSION.md | Short report outline, deliverables checklist, demo script, judge Q&A |
| 09 | 09_MASTER_BUILD_PROMPT.md | The single prompt to paste first; drives the build phase by phase |

## How to use
1. Create an empty folder `terra07-heat-risk/`, put these 10 files in `docs/`.
2. Open your AI agent in that folder. Paste the content of `09_MASTER_BUILD_PROMPT.md`.
3. Let it build phase by phase. After each phase it must run the code and show real output.
4. Run the pipeline ONCE on a machine with internet, **commit the processed data** (small), so the demo works offline on presentation day.

## Non-negotiable rules (the "no gimmick" contract)
1. **Real data only** for the submitted sample area: Landsat surface temperature, Landsat vegetation/built-up indices, Overture/OSM buildings and amenities, WorldPop age structure, Open-Meteo weather. No randomly generated values in the app. A synthetic generator may exist ONLY for unit-test fixtures and must never be used by the app (the app shows a red "SYNTHETIC DATA" banner if it ever loads one).
2. **Every score is explainable exactly**: the score is a weighted sum, so each indicator's contribution is arithmetic, not an approximation.
3. **Every proxy is labelled as a proxy** in the UI and report (e.g. outdoor-worker exposure). No pretending to have census data we don't have.
4. **Every number reproducible**: one command (`make all`) rebuilds data → scores → actions → app inputs. Config in one YAML file; random seeds fixed.
5. **Data provenance shown**: dataset name, date range, resolution, licence visible in the app's "About data" panel.
6. **Limitations stated openly** in the app and report. Honest > impressive.
7. The AI must run the code, fix errors, and never claim something works without executing it.
