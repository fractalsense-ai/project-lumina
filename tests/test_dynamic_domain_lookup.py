"""Tests for dynamic domain lookup, prefix resolution, and discovery operations.

Covers:
- resolve_domain_id prefix / path-style resolution
- list_domain_rbac_roles admin operation
- get_domain_module_manifest admin operation
- Absence of hardcoded domain knowledge in command-interpreter-spec-v1.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumina.core.domain_registry import DomainNotFoundError, DomainRegistry

_REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def registry() -> DomainRegistry:
    """Multi-domain registry from real domain-registry.yaml."""
    return DomainRegistry(
        repo_root=_REPO_ROOT,
        registry_path="domain-packs/system/cfg/domain-registry.yaml",
    )


# ── resolve_domain_id — exact match ────────────────────────────


@pytest.mark.unit
def test_resolve_exact_education(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("education") == "education"


@pytest.mark.unit
def test_resolve_exact_agriculture(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("agriculture") == "agriculture"


@pytest.mark.unit
def test_resolve_exact_system(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("system") == "system"


# ── resolve_domain_id — prefix shorthand ───────────────────────


@pytest.mark.unit
def test_resolve_prefix_edu(registry: DomainRegistry) -> None:
    """'edu' prefix maps to 'education' via module_prefix."""
    assert registry.resolve_domain_id("edu") == "education"


@pytest.mark.unit
def test_resolve_prefix_agri(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("agri") == "agriculture"


@pytest.mark.unit
def test_resolve_prefix_sys(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("sys") == "system"


# ── resolve_domain_id — path-style inputs ──────────────────────


@pytest.mark.unit
def test_resolve_path_domain_edu(registry: DomainRegistry) -> None:
    """'domain/edu' strips prefix and resolves via module_prefix."""
    assert registry.resolve_domain_id("domain/edu") == "education"


@pytest.mark.unit
def test_resolve_path_domain_edu_with_module(registry: DomainRegistry) -> None:
    """'domain/edu/algebra-level-1/v1' extracts 'edu' and resolves."""
    assert registry.resolve_domain_id("domain/edu/algebra-level-1/v1") == "education"


@pytest.mark.unit
def test_resolve_path_domain_agri_with_module(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("domain/agri/operations-level-1/v1") == "agriculture"


@pytest.mark.unit
def test_resolve_path_domain_sys(registry: DomainRegistry) -> None:
    assert registry.resolve_domain_id("domain/sys") == "system"


# ── resolve_domain_id — error cases ───────────────────────────


@pytest.mark.unit
def test_resolve_unknown_raises(registry: DomainRegistry) -> None:
    with pytest.raises(DomainNotFoundError):
        registry.resolve_domain_id("nonexistent")


@pytest.mark.unit
def test_resolve_unknown_path_raises(registry: DomainRegistry) -> None:
    with pytest.raises(DomainNotFoundError):
        registry.resolve_domain_id("domain/zzz/module/v1")


@pytest.mark.unit
def test_resolve_none_returns_default(registry: DomainRegistry) -> None:
    """None domain_id falls back to default_domain (education)."""
    assert registry.resolve_domain_id(None) == "education"


@pytest.mark.unit
def test_resolve_empty_string_returns_default(registry: DomainRegistry) -> None:
    """Empty string is falsy → falls back to default_domain."""
    assert registry.resolve_domain_id("") == "education"


# ── list_modules_for_domain — basic ────────────────────────────


@pytest.mark.unit
def test_list_modules_education(registry: DomainRegistry) -> None:
    """Education domain returns at least one module with an id and physics path."""
    modules = registry.list_modules_for_domain("education")
    assert len(modules) >= 1
    for mod in modules:
        assert "module_id" in mod
        assert "domain_physics_path" in mod


@pytest.mark.unit
def test_list_modules_system(registry: DomainRegistry) -> None:
    modules = registry.list_modules_for_domain("system")
    assert len(modules) >= 1


@pytest.mark.unit
def test_list_modules_unknown_raises(registry: DomainRegistry) -> None:
    with pytest.raises(DomainNotFoundError):
        registry.list_modules_for_domain("nonexistent")


# ── Domain-role-aliases accessible from physics files ──────────


@pytest.mark.unit
def test_system_domain_has_role_aliases() -> None:
    """system-core domain-physics.json contains domain_role_aliases under governance."""
    dp_path = _REPO_ROOT / "domain-packs/system/modules/system-core/domain-physics.json"
    dp = json.loads(dp_path.read_text(encoding="utf-8"))
    aliases = dp["subsystem_configs"]["governance"]["domain_role_aliases"]
    assert isinstance(aliases, dict)
    assert len(aliases) > 0
    # Known aliases: student → user, teacher → user
    assert aliases.get("student") == "user"
    assert aliases.get("teacher") == "user"


# ── Command interpreter spec: no hardcoded domain knowledge ───


_FORBIDDEN_PATTERNS = [
    "algebra-level-1",
    "pre-algebra",
    "algebra-intro",
    "operations-level-1",
]


@pytest.mark.unit
def test_command_interpreter_spec_has_no_hardcoded_modules() -> None:
    """The command interpreter spec must not contain hardcoded module IDs."""
    spec_path = (
        _REPO_ROOT
        / "domain-packs/system/domain-lib/reference/command-interpreter-spec-v1.md"
    )
    content = spec_path.read_text(encoding="utf-8").lower()
    for pattern in _FORBIDDEN_PATTERNS:
        assert pattern not in content, (
            f"Hardcoded module ID '{pattern}' found in command-interpreter-spec"
        )


@pytest.mark.unit
def test_command_interpreter_spec_has_no_hardcoded_domain_roles() -> None:
    """The spec must not enumerate domain-specific roles as known values."""
    spec_path = (
        _REPO_ROOT
        / "domain-packs/system/domain-lib/reference/command-interpreter-spec-v1.md"
    )
    content = spec_path.read_text(encoding="utf-8").lower()
    # These were previously hardcoded in the role-mapping table
    for role in ["field_operator", "site_manager", "teaching_assistant"]:
        assert role not in content, (
            f"Hardcoded domain role '{role}' found in command-interpreter-spec"
        )


@pytest.mark.unit
def test_command_interpreter_spec_mentions_dynamic_discovery() -> None:
    """The spec should reference dynamic discovery operations."""
    spec_path = (
        _REPO_ROOT
        / "domain-packs/system/domain-lib/reference/command-interpreter-spec-v1.md"
    )
    content = spec_path.read_text(encoding="utf-8").lower()
    assert "list_domain_rbac_roles" in content
    assert "get_domain_module_manifest" in content


# ── No remaining night_cycle references in governance files ───


_GOVERNANCE_FILES = [
    "domain-packs/system/modules/system-core/domain-physics.json",
    "domain-packs/system/prompts/domain-persona-v1.md",
    "domain-packs/system/cfg/runtime-config.yaml",
    "domain-packs/system/cfg/admin-operations.yaml",
]


@pytest.mark.unit
@pytest.mark.parametrize("rel_path", _GOVERNANCE_FILES)
def test_no_trigger_night_cycle_in_governance(rel_path: str) -> None:
    fpath = _REPO_ROOT / rel_path
    if not fpath.exists():
        pytest.skip(f"{rel_path} not found")
    content = fpath.read_text(encoding="utf-8")
    assert "trigger_night_cycle" not in content, f"trigger_night_cycle in {rel_path}"
    assert "night_cycle_status" not in content, f"night_cycle_status in {rel_path}"


@pytest.mark.unit
def test_admin_operations_has_daemon_ops() -> None:
    fpath = _REPO_ROOT / "domain-packs" / "system" / "cfg" / "admin-operations.yaml"
    content = fpath.read_text(encoding="utf-8")
    assert "trigger_daemon_task" in content
    assert "daemon_status" in content
    assert "list_domain_rbac_roles" in content
    assert "get_domain_module_manifest" in content
