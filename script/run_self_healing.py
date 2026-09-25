from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

spec = importlib.util.spec_from_file_location(
    "self_healing_pipeline", SRC_DIR / "pipelines" / "self_healing_pipeline.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
auto_heal_pipeline = mod.auto_heal_pipeline

if __name__ == "__main__":
    auto_heal_pipeline()
