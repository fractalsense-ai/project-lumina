"""Tests for TemplateRegistry — template resolution and validation."""

from __future__ import annotations

import pytest

from lumina.staging.template_registry import Template, TemplateRegistry


class TestListIds:
    def test_returns_frozenset(self):
        ids = TemplateRegistry.list_ids()
        assert isinstance(ids, frozenset)

    def test_contains_all_builtin_templates(self):
        ids = TemplateRegistry.list_ids()
        expected = {"domain-physics", "evidence-schema", "tool-adapter",
                    "student-profile", "context-hint"}
        assert expected <= ids


class TestGet:
    def test_known_template(self):
        t = TemplateRegistry.get("domain-physics")
        assert t is not None
        assert isinstance(t, Template)
        assert t.template_id == "domain-physics"

    def test_unknown_returns_none(self):
        assert TemplateRegistry.get("does-not-exist") is None


class TestRequire:
    def test_known_template(self):
        t = TemplateRegistry.require("tool-adapter")
        assert t.template_id == "tool-adapter"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown template_id"):
            TemplateRegistry.require("nope")


class TestTemplateFields:
    """Verify each built-in template has sensible metadata."""

    @pytest.fixture(params=sorted(TemplateRegistry.list_ids()))
    def template(self, request):
        return TemplateRegistry.require(request.param)

    def test_has_description(self, template: Template):
        assert template.description

    def test_has_required_fields(self, template: Template):
        assert len(template.required_fields) >= 1

    def test_has_target_pattern(self, template: Template):
        assert "{" in template.target_pattern  # at least one placeholder

    def test_valid_file_format(self, template: Template):
        assert template.file_format in ("json", "yaml")

    def test_default_structure_is_dict(self, template: Template):
        assert isinstance(template.default_structure, dict)


class TestAllTemplates:
    def test_returns_dict(self):
        all_t = TemplateRegistry.all_templates()
        assert isinstance(all_t, dict)
        assert len(all_t) == len(TemplateRegistry.list_ids())
