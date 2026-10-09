# HeatLens Makefile (Team TERRA07 · Agnitia Hackathon 2026)
.PHONY: setup data score actions app test report all clean

setup:
	python -m pip install -r requirements.txt

data:
	python scripts/run_pipeline.py

score:
	python -c "from heatlens.features import build_features; from heatlens.scoring import score_features, save_scores_geojson; f=build_features(); s=score_features(f); save_scores_geojson(s); print('Scoring complete')"

actions:
	python -c "from heatlens.actions import build_unified_action_plan, save_actions_csv; import geopandas as gpd; g=gpd.read_file('data/processed/scores.geojson'); a=build_unified_action_plan(g); save_actions_csv(a); print('Actions complete')"

test:
	python -m pytest tests/

report:
	python scripts/render_architecture.py
	python scripts/make_report.py
	python scripts/render_pdf_report.py

app:
	streamlit run app/streamlit_app.py

all: data report test
	@echo "HeatLens End-to-End Pipeline, Reports and Test Verification Complete!"

clean:
	rm -rf .pytest_cache __pycache__
