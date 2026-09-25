from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("=== [BONUS B3] Running End-to-End Automated Test Suite (Pytest) ===")
    test_dir = ROOT / "tests"
    args = [str(test_dir), "-v", "--tb=short"]
    exit_code = pytest.main(args)
    if exit_code == 0:
        print("\n[SUCCESS] ALL TESTS PASSED! Test suite coverage meets requirements.")
    else:
        print(f"\n[FAILURE] Tests finished with exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
