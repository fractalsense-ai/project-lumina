from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REF_IMPL = REPO_ROOT / "reference-implementations"

if str(REF_IMPL) not in sys.path:
    sys.path.insert(0, str(REF_IMPL))
