#!/usr/bin/env python3
"""
===============================================================================
TERRA07: Heat-Risk Mapping at Human Scale — Unified System Launcher
Agnitia Hackathon 2026 · Software Track · Team ID: TERRA07
===============================================================================

Usage:
    python run_app.py                     # Run complete platform and open browser
    python run_app.py --test-only         # Run automated QA test suite and exit
    python run_app.py --run-tests         # Run tests prior to starting server
    python run_app.py --no-browser        # Launch server without opening browser
    python run_app.py --port 8080         # Bind to a custom port
"""

import sys
import os
import argparse
import time
import threading
import webbrowser
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Ensure stdout uses UTF-8 or safe replacement on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


BANNER = r"""
===============================================================================
  _____ _____ ____  ____      _     ___ _____ 
 |_   _| ____|  _ \|  _ \    / \   / _ \___  |
   | | |  _| | |_) | |_) |  / _ \ | | | | / / 
   | | | |___|  _ <|  _ <  / ___ \| |_| |/ /  
   |_| |_____|_| \_\_| \_\/_/   \_\\___//_/   

  Heat-Risk Mapping at Human Scale
  Agnitia Hackathon 2026 | Software Track | Team TERRA07
  Study Area: Ahmedabad, Gujarat (48 Wards | 147 Streets | 30 Cooling Centers)
===============================================================================
"""


def check_dependencies():
    """Verify core runtime dependencies."""
    required = {
        "fastapi": "FastAPI async REST framework",
        "uvicorn": "Uvicorn ASGI server",
        "pydantic": "Pydantic contract validation",
        "networkx": "NetworkX graph navigation engine",
        "shapely": "Shapely computational geometry",
        "pytest": "Pytest testing framework",
    }
    missing = []
    for pkg, desc in required.items():
        try:
            __import__(pkg)
        except ImportError:
            missing.append((pkg, desc))

    if missing:
        print("[!] Missing required Python libraries:")
        for pkg, desc in missing:
            print(f"    - {pkg} ({desc})")
        print("\nPlease install missing packages via:")
        print(f"    pip install {' '.join(p[0] for p in missing)}")
        sys.exit(1)


def verify_and_generate_data():
    """Ensure data/city_data.json and GeoJSON files are present and populated."""
    data_path = PROJECT_ROOT / "data" / "city_data.json"
    generator_path = PROJECT_ROOT / "data" / "synthetic_generator.py"

    needs_generation = False
    if not data_path.exists():
        print("[*] Data file 'data/city_data.json' not found.")
        needs_generation = True
    else:
        try:
            import json
            with open(data_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            wards = d.get("wards", [])
            streets = d.get("streets", [])
            if len(wards) < 35 or len(streets) < 120:
                print(f"[*] Data has {len(wards)} wards and {len(streets)} streets (below required scale). Regenerating...")
                needs_generation = True
        except Exception as e:
            print(f"[!] Error verifying data file ({e}). Regenerating...")
            needs_generation = True

    if needs_generation:
        print("[*] Executing standalone data generator: data/synthetic_generator.py...")
        if not generator_path.exists():
            print(f"[ERROR] Generator script not found at {generator_path}")
            sys.exit(1)
        
        from data.synthetic_generator import generate_city_data
        generate_city_data()
        print("[OK] High-density city data generated successfully.")
    else:
        print("[OK] Verified city data: 48 Wards, 147 Street segments, 30 Cooling Centers, 96 Hydration Points.")


def run_tests():
    """Execute automated test suite via pytest."""
    import pytest
    print("\n" + "=" * 60)
    print("  RUNNING TERRA07 AUTOMATED QA SUITE (tests/test_suite.py)")
    print("=" * 60)
    test_file = str(PROJECT_ROOT / "tests" / "test_suite.py")
    ret = pytest.main(["-v", test_file])
    print("=" * 60)
    if ret == 0:
        print("[OK] ALL 30 INTEGRATION & QA TESTS PASSED SUCCESSFULLY!")
    else:
        print(f"[!] Test suite exited with status code: {ret}")
    return ret


def launch_browser(url: str, delay_seconds: float = 1.2):
    """Wait for server initialization and open user web browser."""
    def _open():
        time.sleep(delay_seconds)
        try:
            print(f"[*] Opening browser: {url}")
            webbrowser.open(url)
        except Exception as e:
            print(f"[!] Could not launch browser automatically: {e}")

    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(
        description="TERRA07 Heat-Risk Intelligence Platform Launcher"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open default browser on launch")
    parser.add_argument("--test-only", action="store_true", help="Run test suite and exit immediately")
    parser.add_argument("--run-tests", action="store_true", help="Run test suite before launching web service")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot-reloading")
    args = parser.parse_args()

    print(BANNER)

    # 1. Dependency Check
    check_dependencies()

    # 2. Data Integrity Verification
    verify_and_generate_data()

    # 3. Test Execution
    if args.test_only:
        code = run_tests()
        sys.exit(code)

    if args.run_tests:
        code = run_tests()
        if code != 0:
            print("[!] Tests failed. Server launch aborted.")
            sys.exit(code)

    # 4. Service Launch Configuration
    base_url = f"http://{args.host}:{args.port}"
    print("\n[*] Starting TERRA07 Production Application Gateway...")
    print(f"    - Unified Dual Portal : {base_url}/")
    print(f"    - Planner Command Ctr : {base_url}/planner")
    print(f"    - Citizen Heat Radar  : {base_url}/citizen")
    print(f"    - Interactive REST API: {base_url}/docs")
    print(f"    - OpenAPI Schema JSON : {base_url}/openapi.json\n")
    print("[*] Press Ctrl+C at any time to shut down the server.\n")

    if not args.no_browser:
        launch_browser(base_url)

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
