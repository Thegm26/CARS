from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path


def get_pricing_module():
    candidate_path = os.environ.get("CARS_PRICING_PATH")
    if not candidate_path:
        return importlib.import_module("cars_store.pricing")

    module_path = Path(candidate_path).resolve()
    spec = importlib.util.spec_from_file_location("candidate_pricing", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load pricing module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_pricing"] = module
    spec.loader.exec_module(module)
    return module
