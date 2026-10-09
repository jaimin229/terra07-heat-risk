"""
TERRA07 Heat-Risk Intelligence Engine - Main FastAPI Application
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale

FastAPI Backend Lead: Agent 7 (Geospatial API Lead)
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.data_store import store
from backend.engine import router_engine
from backend.routes import router as api_router
from backend.schemas import RootMetadataResponse

# Base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Event Handler.
    Auto-loads the city dataset on startup and prepares the routing graph.
    """
    print("[TERRA07] Starting up Heat-Risk Intelligence Engine...")
    start_time = time.perf_counter()

    # 1. Initialize and cache City Data Store
    store.initialize()
    print(f"[TERRA07] Loaded {len(store.wards)} wards, {len(store.streets)} streets, "
          f"{len(store.cooling_centers)} cooling centers, and {len(store.hydration_points)} hydration posts.")

    # 2. Warm up NetworkX cool-path routing graph
    router_engine.build_graph()
    print(f"[TERRA07] Routing graph initialized with {router_engine.graph.number_of_nodes()} nodes "
          f"and {router_engine.graph.number_of_edges()} edges.")

    elapsed = round((time.perf_counter() - start_time) * 1000, 2)
    print(f"[TERRA07] System startup completed in {elapsed}ms. Ready to serve requests.")
    yield
    print("[TERRA07] Shutting down Heat-Risk Intelligence Engine.")


# ---------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------

app = FastAPI(
    title="TERRA07 Heat-Risk Intelligence Engine",
    description=(
        "Production-grade, human-scale microclimate heat vulnerability, "
        "explainable AI (XAI) feature attribution, cool-path pedestrian navigation, "
        "and dynamic climate scenario simulation for Agnitia Hackathon 2026."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ---------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits cross-origin requests from any frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": "HTTP Exception",
            "message": exc.detail,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", [])])
        msg = err.get("msg", "Invalid parameter")
        errors.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status_code": 422,
            "error": "Request Validation Error",
            "message": "The request body or query parameters did not pass validation.",
            "details": errors,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "error": "Internal Server Error",
            "message": str(exc),
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# ---------------------------------------------------------
# Root Endpoint (GET /)
# ---------------------------------------------------------

@app.get(
    "/",
    response_model=RootMetadataResponse,
    summary="Root System Metadata & Health",
    description="Returns Agnitia Hackathon TERRA07 branding, operational health status, target urban domain, and primary API directory."
)
async def root_endpoint(request: Request):
    # Check if client explicitly requests HTML and frontend index exists
    accept_header = request.headers.get("accept", "")
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if "text/html" in accept_header and os.path.exists(index_file) and not request.query_params.get("format") == "json":
        return FileResponse(index_file)

    return RootMetadataResponse(
        system="TERRA07 Heat-Risk Intelligence Engine",
        project="Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale",
        team="Team TERRA07",
        lead="Agent 7 (FastAPI Backend & Geospatial API Lead)",
        version="1.0.0",
        status="healthy",
        city="Ahmedabad Metropolitan Region",
        description=(
            "Human-scale urban heat risk intelligence system integrating high-resolution Land Surface Temperature (LST), "
            "Normalized Difference Vegetation Index (NDVI), Mean Radiant Temperature (Tmrt), street shade ratios, "
            "demographic sensitivity, SHAP-driven XAI diagnosis, Dijkstra cool-path navigation, and dynamic heatwave scenario stress-testing."
        ),
        endpoints={
            "root_metadata": "GET /",
            "interactive_docs": "GET /docs",
            "city_overview": "GET /api/overview",
            "ward_profiles": "GET /api/wards",
            "ward_detail": "GET /api/wards/{ward_id}",
            "human_scale_streets": "GET /api/streets",
            "xai_explanation": "GET /api/explain/{entity_type}/{id}",
            "intervention_recommendations": "POST /api/interventions/recommend",
            "cool_path_routing": "POST /api/routing/cool-path",
            "scenario_simulation": "POST /api/simulate/scenario",
            "public_heat_advice": "GET /api/public/advice",
            "cooling_centers": "GET /api/cooling-centers",
            "hydration_points": "GET /api/hydration-points",
            "static_assets": "GET /static"
        },
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------
# Mount API Router
# ---------------------------------------------------------

app.include_router(api_router)


# ---------------------------------------------------------
# Static File Serving for Frontend
# ---------------------------------------------------------

os.makedirs(FRONTEND_DIR, exist_ok=True)

# Mount /static to serve frontend assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


@app.get("/ui", include_in_schema=False)
@app.get("/app", include_in_schema=False)
@app.get("/portal", include_in_schema=False)
async def serve_frontend_ui():
    """Direct route to access the unified frontend portal."""
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(
        status_code=404,
        content={"message": "Frontend index.html is being prepared by the Frontend team in /frontend."}
    )


@app.get("/planner", include_in_schema=False)
async def serve_planner_ui():
    """Direct route to Urban Planner Command Center."""
    planner_file = os.path.join(FRONTEND_DIR, "planner_view.html")
    if os.path.exists(planner_file):
        return FileResponse(planner_file)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/citizen", include_in_schema=False)
async def serve_citizen_ui():
    """Direct route to Citizen Heat Advisory & Cool Walk Portal."""
    public_file = os.path.join(FRONTEND_DIR, "public_view.html")
    if os.path.exists(public_file):
        return FileResponse(public_file)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
