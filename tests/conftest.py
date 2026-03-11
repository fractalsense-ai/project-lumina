from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REF_IMPL = REPO_ROOT / "reference-implementations"

if str(REF_IMPL) not in sys.path:
    sys.path.insert(0, str(REF_IMPL))

# Register hyphenated filenames as importable modules.
if "dsa_orchestrator" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "dsa_orchestrator", str(REF_IMPL / "dsa-orchestrator.py")
    )
    _mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
    sys.modules["dsa_orchestrator"] = _mod
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
