"""Unit tests for DomainRegistry.resolve_default_for_user().

These tests exercise the role-based default domain resolution logic
introduced to route system-level operators to the system domain instead
of the global default_domain (education).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lumina.core.domain_registry import DomainRegistry

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def registry() -> DomainRegistry:
    """Load DomainRegistry in multi-domain mode from the real registry YAML."""
    return DomainRegistry(
        repo_root=_REPO_ROOT,
        registry_path="cfg/domain-registry.yaml",
        # No load_runtime_context_fn needed — we only test resolve_default_for_user
    )


# ── resolve_default_for_user() ────────────────────────────────


@pytest.mark.unit
def test_unauthenticated_user_returns_global_default(registry: DomainRegistry) -> None:
    """None user (unauthenticated) → global default_domain (education)."""
    result = registry.resolve_default_for_user(None)
    assert result == "education"


@pytest.mark.unit
def test_root_role_returns_system(registry: DomainRegistry) -> None:
    """root role → system domain (via role_defaults)."""
    user = {"sub": "root_001", "role": "root", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "system"


@pytest.mark.unit
def test_it_support_role_returns_system(registry: DomainRegistry) -> None:
    """it_support role → system domain (via role_defaults)."""
    user = {"sub": "its_001", "role": "it_support", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "system"


@pytest.mark.unit
def test_qa_role_returns_global_default(registry: DomainRegistry) -> None:
    """qa role is not in role_defaults → falls through to global default (education)."""
    user = {"sub": "qa_001", "role": "qa", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_auditor_role_returns_global_default(registry: DomainRegistry) -> None:
    """auditor role is not in role_defaults → falls through to global default (education)."""
    user = {"sub": "aud_001", "role": "auditor", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_user_role_returns_global_default(registry: DomainRegistry) -> None:
    """user role falls through to global default (education)."""
    user = {"sub": "usr_001", "role": "user", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_domain_authority_with_edu_module_returns_education(registry: DomainRegistry) -> None:
    """domain_authority with a domain/edu/… module → education domain."""
    user = {
        "sub": "da_001",
        "role": "domain_authority",
        "governed_modules": ["domain/edu/algebra-level-1/v1"],
    }
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_domain_authority_with_agri_module_returns_agriculture(registry: DomainRegistry) -> None:
    """domain_authority with a domain/agri/… module → agriculture domain."""
    user = {
        "sub": "da_agri_001",
        "role": "domain_authority",
        "governed_modules": ["domain/agri/operations-level-1/v1"],
    }
    assert registry.resolve_default_for_user(user) == "agriculture"


@pytest.mark.unit
def test_domain_authority_empty_governed_modules_returns_global_default(
    registry: DomainRegistry,
) -> None:
    """domain_authority with empty governed_modules cannot infer prefix → global default."""
    user = {"sub": "da_002", "role": "domain_authority", "governed_modules": []}
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_domain_authority_unknown_prefix_returns_global_default(
    registry: DomainRegistry,
) -> None:
    """domain_authority with an unregistered module prefix → global default."""
    user = {
        "sub": "da_003",
        "role": "domain_authority",
        "governed_modules": ["domain/zzz/unknown-module/v1"],
    }
    assert registry.resolve_default_for_user(user) == "education"


@pytest.mark.unit
def test_domain_authority_uses_first_governed_module_only(registry: DomainRegistry) -> None:
    """When multiple governed_modules are present, only the first is used for inference."""
    user = {
        "sub": "da_004",
        "role": "domain_authority",
        "governed_modules": [
            "domain/edu/algebra-level-1/v1",
            "domain/agri/operations-level-1/v1",
        ],
    }
    assert registry.resolve_default_for_user(user) == "education"


# ── Single-domain mode: resolve_default_for_user() still works ───────────


@pytest.mark.unit
def test_single_domain_mode_always_returns_default(tmp_path: Path) -> None:
    """In single-domain mode, resolve_default_for_user returns the single domain regardless of role."""
    # Point at a real runtime config so the registry initialises without error
    reg = DomainRegistry(
        repo_root=_REPO_ROOT,
        single_config_path="domain-packs/education/cfg/runtime-config.yaml",
    )
    for role in ("root", "it_support", "qa", "auditor", "user"):
        result = reg.resolve_default_for_user({"sub": "u", "role": role, "governed_modules": []})
        assert result == "_default", f"Expected '_default' for role {role!r}, got {result!r}"
