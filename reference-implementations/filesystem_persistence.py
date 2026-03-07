from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from persistence_adapter import PersistenceAdapter


class FilesystemPersistenceAdapter(PersistenceAdapter):
    """Filesystem-backed persistence preserving current reference behavior."""

    def __init__(self, repo_root: Path, ctl_dir: Path) -> None:
        self.repo_root = repo_root
        self.ctl_dir = ctl_dir
        self.session_dir = self.ctl_dir / "sessions"
        self.ctl_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._load_yaml = self._load_yaml_loader()

    def _load_yaml_loader(self):
        yaml_loader_path = self.repo_root / "reference-implementations" / "yaml-loader.py"
        spec = importlib.util.spec_from_file_location("persistence_yaml_loader", str(yaml_loader_path))
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules["persistence_yaml_loader"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.load_yaml

    def load_domain_physics(self, path: str) -> dict[str, Any]:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def load_subject_profile(self, path: str) -> dict[str, Any]:
        return self._load_yaml(path)

    def get_ctl_ledger_path(self, session_id: str) -> str:
        return str(self.ctl_dir / f"session-{session_id}.jsonl")

    def append_ctl_record(self, session_id: str, record: dict[str, Any], ledger_path: str | None = None) -> None:
        target_path = Path(ledger_path) if ledger_path else Path(self.get_ctl_ledger_path(session_id))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            fh.write("\n")

    def load_session_state(self, session_id: str) -> dict[str, Any] | None:
        path = self.session_dir / f"session-{session_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None

    def save_session_state(self, session_id: str, state: dict[str, Any]) -> None:
        path = self.session_dir / f"session-{session_id}.json"
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
        tmp.replace(path)
