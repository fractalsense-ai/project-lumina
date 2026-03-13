"""Tests for lumina.systools.yaml_converter — YAML → JSON converter."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from lumina.systools.yaml_converter import (
    compute_hash,
    convert,
    load_yaml,
    validate_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── helpers ────────────────────────────────────────────────────────────────────


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── load_yaml ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_load_yaml_basic(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    _write_yaml(yaml_file, "id: my-domain\nversion: 1.0.0\n")
    data = load_yaml(yaml_file)
    assert data["id"] == "my-domain"
    assert data["version"] == "1.0.0"


@pytest.mark.unit
def test_load_yaml_complex(tmp_path: Path) -> None:
    _write_yaml(tmp_path / "t.yaml", "key: value\nlist:\n  - a\n  - b\n")
    data = load_yaml(tmp_path / "t.yaml")
    assert data["key"] == "value"
    assert data["list"] == ["a", "b"]


# ── compute_hash ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_compute_hash_is_deterministic() -> None:
    data = {"id": "test", "version": "1.0.0"}
    h1 = compute_hash(data)
    h2 = compute_hash(data)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


@pytest.mark.unit
def test_compute_hash_differs_for_different_data() -> None:
    assert compute_hash({"a": 1}) != compute_hash({"a": 2})


# ── validate_schema ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_schema_passes_valid_data(tmp_path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    errors = validate_schema({"id": "hello"}, schema_path)
    assert errors == []


@pytest.mark.unit
def test_validate_schema_fails_missing_required(tmp_path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    errors = validate_schema({"name": "no-id"}, schema_path)
    assert len(errors) > 0


# ── convert ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_convert_basic(tmp_path: Path) -> None:
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "id: test-domain\nversion: 2.0.0\n")
    out = tmp_path / "domain.json"

    result = convert(yaml_path=yaml_file, output_path=out)
    assert result == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["id"] == "test-domain"


@pytest.mark.unit
def test_convert_default_output_path(tmp_path: Path) -> None:
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "id: test\nversion: 1.0.0\n")

    result = convert(yaml_path=yaml_file)
    assert result == 0
    expected = yaml_file.with_suffix(".json")
    assert expected.exists()


@pytest.mark.unit
def test_convert_dry_run_does_not_write(tmp_path: Path) -> None:
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "id: test\nversion: 1.0.0\n")
    out = tmp_path / "domain.json"

    result = convert(yaml_path=yaml_file, output_path=out, dry_run=True)
    assert result == 0
    assert not out.exists()


@pytest.mark.unit
def test_convert_missing_file_returns_1(tmp_path: Path) -> None:
    result = convert(yaml_path=tmp_path / "nonexistent.yaml")
    assert result == 1


@pytest.mark.unit
def test_convert_non_dict_yaml_returns_1(tmp_path: Path) -> None:
    yaml_file = tmp_path / "list.yaml"
    _write_yaml(yaml_file, "- item1\n- item2\n")
    result = convert(yaml_path=yaml_file)
    assert result == 1


@pytest.mark.unit
def test_convert_with_schema_valid(tmp_path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "id: valid-domain\n")

    result = convert(yaml_path=yaml_file, schema_path=schema_path)
    assert result == 0


@pytest.mark.unit
def test_convert_with_schema_invalid_returns_1(tmp_path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "name: no-id-field\n")

    result = convert(yaml_path=yaml_file, schema_path=schema_path)
    assert result == 1


@pytest.mark.unit
def test_convert_missing_schema_returns_1(tmp_path: Path) -> None:
    yaml_file = tmp_path / "domain.yaml"
    _write_yaml(yaml_file, "id: test\n")
    result = convert(yaml_path=yaml_file, schema_path=tmp_path / "missing-schema.json")
    assert result == 1


# ── main via sys.argv ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_main_exits_0_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lumina.systools.yaml_converter import main

    yaml_file = tmp_path / "test.yaml"
    _write_yaml(yaml_file, "id: main-test\nversion: 1.0.0\n")

    monkeypatch.setattr(sys, "argv", ["yaml_converter", str(yaml_file), "--dry-run"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


@pytest.mark.unit
def test_main_exits_1_on_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lumina.systools.yaml_converter import main

    monkeypatch.setattr(sys, "argv", ["yaml_converter", str(tmp_path / "nope.yaml")])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
