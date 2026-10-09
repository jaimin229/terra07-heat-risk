import sys
import os
from pathlib import Path

# Add project root to sys.path so modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure data store and routing graph are initialized for serverless execution
from backend.data_store import store
from backend.engine import router_engine

if not store._initialized:
    store.initialize()
if router_engine.graph is None or router_engine.graph.number_of_nodes() == 0:
    router_engine.build_graph()

from backend.main import app
