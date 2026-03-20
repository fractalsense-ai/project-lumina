"""Tests for the Inspection Middleware pipeline and its sub-modules.

Covers:
- InspectionPipeline (pipeline.py) — full chain tests
- output_validator.py — schema validation & sanitisation
- invariant_checker.py — expression evaluator & batch evaluator
- nlp_preprocessor.py — NLP primitives & extractor runner
"""

from __future__ import annotations

import pytest

from lumina.middleware.invariant_checker import (
    evaluate_check_expr,
    evaluate_invariants,
    parse_check_literal,
)
from lumina.middleware.nlp_preprocessor import (
    NLPAnchor,
    NLPPreprocessResult,
    caps_ratio,
    keyword_match,
    punctuation_density,
    regex_extract,
    run_extractors,
    vocab_overlap_ratio,
)
from lumina.middleware.output_validator import sanitize_output, validate_output
from lumina.middleware.pipeline import InspectionPipeline, InspectionResult


# ═══════════════════════════════════════════════════════════════
#  parse_check_literal
# ═══════════════════════════════════════════════════════════════


class TestParseCheckLiteral:
    def test_empty_list(self):
        assert parse_check_literal("[]") == []

    def test_true(self):
        assert parse_check_literal("true") is True
        assert parse_check_literal("True") is True

    def test_false(self):
        assert parse_check_literal("false") is False

    def test_int(self):
        assert parse_check_literal("42") == 42
        assert isinstance(parse_check_literal("42"), int)

    def test_negative_int(self):
        assert parse_check_literal("-3") == -3

    def test_float(self):
        result = parse_check_literal("3.14")
        assert abs(result - 3.14) < 1e-9
        assert isinstance(result, float)

    def test_string_fallback(self):
        assert parse_check_literal("some_field") == "some_field"

    def test_whitespace_stripped(self):
        assert parse_check_literal("  42  ") == 42


# ═══════════════════════════════════════════════════════════════
#  evaluate_check_expr
# ═══════════════════════════════════════════════════════════════


class TestEvaluateCheckExpr:
    # ── Truthy checks ──
    def test_truthy_present(self):
        assert evaluate_check_expr("x", {"x": 1}) is True

    def test_truthy_false_value(self):
        assert evaluate_check_expr("x", {"x": 0}) is False

    def test_truthy_missing_field(self):
        assert evaluate_check_expr("x", {}) is None

    def test_truthy_none_value(self):
        assert evaluate_check_expr("x", {"x": None}) is None

    # ── Equality / inequality ──
    def test_eq_match(self):
        assert evaluate_check_expr("x == 5", {"x": 5}) is True

    def test_eq_mismatch(self):
        assert evaluate_check_expr("x == 5", {"x": 3}) is False

    def test_ne(self):
        assert evaluate_check_expr("x != 0", {"x": 1}) is True

    def test_eq_bool_true(self):
        assert evaluate_check_expr("active == true", {"active": True}) is True

    def test_eq_bool_false(self):
        assert evaluate_check_expr("active == false", {"active": False}) is True

    def test_eq_empty_list(self):
        assert evaluate_check_expr("items == []", {"items": []}) is True

    # ── Numeric comparisons ──
    def test_gte_pass(self):
        assert evaluate_check_expr("score >= 0.5", {"score": 0.7}) is True

    def test_gte_boundary(self):
        assert evaluate_check_expr("score >= 0.5", {"score": 0.5}) is True

    def test_gte_fail(self):
        assert evaluate_check_expr("score >= 0.5", {"score": 0.3}) is False

    def test_lte(self):
        assert evaluate_check_expr("count <= 10", {"count": 10}) is True
        assert evaluate_check_expr("count <= 10", {"count": 11}) is False

    def test_gt(self):
        assert evaluate_check_expr("x > 0", {"x": 1}) is True
        assert evaluate_check_expr("x > 0", {"x": 0}) is False

    def test_lt(self):
        assert evaluate_check_expr("x < 100", {"x": 50}) is True
        assert evaluate_check_expr("x < 100", {"x": 100}) is False

    # ── Field-reference RHS ──
    def test_field_reference_rhs(self):
        evidence = {"step_count": 5, "min_steps": 3}
        assert evaluate_check_expr("step_count >= min_steps", evidence) is True

    def test_field_reference_rhs_missing(self):
        assert evaluate_check_expr("step_count >= min_steps", {"step_count": 5}) is None

    # ── Missing evidence field ──
    def test_missing_lhs(self):
        assert evaluate_check_expr("x == 5", {}) is None

    # ── Malformed expression ──
    def test_two_token_malformed(self):
        assert evaluate_check_expr("x ==", {"x": 1}) is None


# ═══════════════════════════════════════════════════════════════
#  evaluate_invariants
# ═══════════════════════════════════════════════════════════════


class TestEvaluateInvariants:
    def test_passing_invariant(self):
        invariants = [
            {"id": "score_range", "check": "score >= 0.0", "severity": "critical"},
        ]
        results = evaluate_invariants(invariants, {"score": 0.5})
        assert len(results) == 1
        assert results[0]["passed"] is True

    def test_failing_critical(self):
        invariants = [
            {"id": "score_range", "check": "score >= 0.0", "severity": "critical"},
        ]
        results = evaluate_invariants(invariants, {"score": -1.0})
        assert len(results) == 1
        assert results[0]["passed"] is False
        assert results[0]["severity"] == "critical"

    def test_handled_by_skipped(self):
        invariants = [
            {"id": "delegated", "check": "x == 1", "handled_by": "domain_lib"},
        ]
        results = evaluate_invariants(invariants, {"x": 99})
        assert results == []

    def test_missing_check_skipped(self):
        invariants = [{"id": "no_check", "severity": "warning"}]
        results = evaluate_invariants(invariants, {})
        assert results == []

    def test_missing_evidence_skipped(self):
        invariants = [
            {"id": "missing", "check": "nonexistent >= 0", "severity": "warning"},
        ]
        results = evaluate_invariants(invariants, {})
        assert results == []

    def test_multiple_invariants(self):
        invariants = [
            {"id": "a", "check": "x >= 0", "severity": "critical"},
            {"id": "b", "check": "y == true", "severity": "warning"},
        ]
        results = evaluate_invariants(invariants, {"x": 1, "y": False})
        assert len(results) == 2
        assert results[0]["passed"] is True
        assert results[1]["passed"] is False

    def test_standing_order_propagated(self):
        invariants = [
            {
                "id": "limit",
                "check": "x >= 0",
                "severity": "warning",
                "standing_order_on_violation": "escalate",
            },
        ]
        results = evaluate_invariants(invariants, {"x": 1})
        assert results[0]["standing_order_on_violation"] == "escalate"


# ═══════════════════════════════════════════════════════════════
#  validate_output
# ═══════════════════════════════════════════════════════════════


class TestValidateOutput:
    def test_valid_payload(self):
        schema = {
            "answer": {"type": "string", "required": True},
            "confidence": {"type": "number"},
        }
        ok, violations = validate_output(
            {"answer": "hello", "confidence": 0.9}, schema
        )
        assert ok is True
        assert violations == []

    def test_missing_required(self):
        schema = {"answer": {"type": "string", "required": True}}
        ok, violations = validate_output({}, schema)
        assert ok is False
        assert any("Missing required" in v for v in violations)

    def test_type_mismatch(self):
        schema = {"score": {"type": "number"}}
        ok, violations = validate_output({"score": "not a number"}, schema)
        assert ok is False
        assert any("Type mismatch" in v for v in violations)

    def test_enum_violation(self):
        schema = {"action": {"type": "string", "enum": ["add", "remove"]}}
        ok, violations = validate_output({"action": "update"}, schema)
        assert ok is False
        assert any("not in" in v for v in violations)

    def test_minimum_violation(self):
        schema = {"score": {"type": "number", "minimum": 0.0}}
        ok, violations = validate_output({"score": -1.0}, schema)
        assert ok is False
        assert any("below minimum" in v for v in violations)

    def test_maximum_violation(self):
        schema = {"score": {"type": "number", "maximum": 1.0}}
        ok, violations = validate_output({"score": 1.5}, schema)
        assert ok is False
        assert any("above maximum" in v for v in violations)

    def test_extra_fields_allowed(self):
        """Fields not in schema are silently passed through."""
        schema = {"known": {"type": "string"}}
        ok, violations = validate_output(
            {"known": "ok", "_extra": 42}, schema
        )
        assert ok is True

    def test_bool_not_integer(self):
        schema = {"count": {"type": "integer"}}
        ok, violations = validate_output({"count": True}, schema)
        assert ok is False

    def test_optional_missing_no_violation(self):
        schema = {"opt": {"type": "string"}}
        ok, violations = validate_output({}, schema)
        assert ok is True


class TestSanitizeOutput:
    def test_fills_defaults(self):
        schema = {"score": {"type": "number", "default": 0.5}}
        result = sanitize_output({}, schema)
        assert result["score"] == 0.5

    def test_does_not_overwrite(self):
        schema = {"score": {"type": "number", "default": 0.5}}
        result = sanitize_output({"score": 0.9}, schema)
        assert result["score"] == 0.9

    def test_preserves_extra_fields(self):
        schema = {"a": {"type": "string", "default": "x"}}
        result = sanitize_output({"extra": 1}, schema)
        assert result["extra"] == 1
        assert result["a"] == "x"


# ═══════════════════════════════════════════════════════════════
#  NLP Primitives
# ═══════════════════════════════════════════════════════════════


class TestKeywordMatch:
    def test_match(self):
        assert keyword_match("I need help with algebra", ["help", "stuck"]) is True

    def test_no_match(self):
        assert keyword_match("Everything is fine", ["help", "stuck"]) is False

    def test_case_insensitive(self):
        assert keyword_match("HELP ME", ["help"]) is True

    def test_case_sensitive(self):
        assert keyword_match("HELP ME", ["help"], case_sensitive=True) is False


class TestRegexExtract:
    def test_basic_match(self):
        result = regex_extract("x = 42", r"x\s*=\s*(\d+)", group=1)
        assert result == "42"

    def test_no_match(self):
        assert regex_extract("hello world", r"\d+") is None

    def test_group_zero(self):
        result = regex_extract("score: 95", r"\d+")
        assert result == "95"


class TestVocabOverlap:
    def test_full_overlap(self):
        assert vocab_overlap_ratio("add subtract", {"add", "subtract"}) == 1.0

    def test_no_overlap(self):
        assert vocab_overlap_ratio("hello world", {"foo", "bar"}) == 0.0

    def test_partial(self):
        ratio = vocab_overlap_ratio("one two three", {"one", "three"})
        assert abs(ratio - 2 / 3) < 1e-9

    def test_empty_text(self):
        assert vocab_overlap_ratio("", {"a"}) == 0.0


class TestCapsRatio:
    def test_all_caps(self):
        assert caps_ratio("ABC") == 1.0

    def test_no_caps(self):
        assert caps_ratio("abc") == 0.0

    def test_mixed(self):
        assert abs(caps_ratio("AbCd") - 0.5) < 1e-9

    def test_no_alpha(self):
        assert caps_ratio("123") == 0.0


class TestPunctuationDensity:
    def test_no_punct(self):
        assert punctuation_density("hello") == 0.0

    def test_all_punct(self):
        assert punctuation_density("!!!") == 1.0

    def test_empty(self):
        assert punctuation_density("") == 0.0


# ═══════════════════════════════════════════════════════════════
#  NLP Extractor Runner
# ═══════════════════════════════════════════════════════════════


class TestRunExtractors:
    def test_collects_anchors(self):
        def extract_number(text, ctx):
            import re
            m = re.search(r"\d+", text)
            if m:
                return NLPAnchor(key="number", value=int(m.group()))
            return None

        result = run_extractors("answer is 42", {}, [extract_number])
        assert len(result.anchors) == 1
        assert result.anchors[0].key == "number"
        assert result.anchors[0].value == 42
        assert result.evidence_partial["number"] == 42
        assert "NLP signals" in result.anchor_summary

    def test_none_extractors_skipped(self):
        result = run_extractors("text", {}, [lambda t, c: None])
        assert result.anchors == []
        assert result.evidence_partial == {}

    def test_empty_extractors(self):
        result = run_extractors("text", {}, [])
        assert result.anchors == []


class TestNLPPreprocessResultMerge:
    def test_merge_does_not_overwrite(self):
        r = NLPPreprocessResult(evidence_partial={"x": 10})
        merged = r.merge_into({"x": 99, "y": 1})
        assert merged["x"] == 99  # LLM value preserved
        assert merged["y"] == 1

    def test_merge_adds_missing(self):
        r = NLPPreprocessResult(evidence_partial={"z": 42})
        merged = r.merge_into({"y": 1})
        assert merged["z"] == 42
        assert merged["y"] == 1


# ═══════════════════════════════════════════════════════════════
#  InspectionPipeline
# ═══════════════════════════════════════════════════════════════


class TestInspectionPipeline:
    def test_empty_pipeline_approves(self):
        """No schema, no invariants → approved."""
        pipe = InspectionPipeline()
        result = pipe.run({"anything": "goes"})
        assert result.approved is True
        assert result.violations == []

    def test_valid_payload_approved(self):
        schema = {
            "answer": {"type": "string", "required": True},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        }
        pipe = InspectionPipeline(turn_input_schema=schema)
        result = pipe.run({"answer": "hello", "confidence": 0.8})
        assert result.approved is True
        assert result.violations == []

    def test_schema_violation_strict_denies(self):
        schema = {"answer": {"type": "string", "required": True}}
        pipe = InspectionPipeline(turn_input_schema=schema, strict=True)
        result = pipe.run({})
        assert result.approved is False
        assert any("Missing required" in v for v in result.violations)

    def test_schema_violation_permissive_approves(self):
        schema = {"answer": {"type": "string", "required": True}}
        pipe = InspectionPipeline(turn_input_schema=schema, strict=False)
        result = pipe.run({})
        assert result.approved is True
        assert len(result.violations) > 0  # Still recorded

    def test_critical_invariant_denies(self):
        invariants = [
            {"id": "positive_score", "check": "score >= 0", "severity": "critical"},
        ]
        pipe = InspectionPipeline(invariants=invariants)
        result = pipe.run({"score": -1})
        assert result.approved is False
        assert any("positive_score" in v for v in result.violations)

    def test_warning_invariant_approves(self):
        invariants = [
            {"id": "soft_limit", "check": "x <= 100", "severity": "warning"},
        ]
        pipe = InspectionPipeline(invariants=invariants)
        result = pipe.run({"x": 200})
        assert result.approved is True
        assert len(result.violations) > 0

    def test_nlp_extractors_merged(self):
        def detect_greeting(text, ctx):
            if "hello" in text.lower():
                return NLPAnchor(key="greeting", value=True)
            return None

        pipe = InspectionPipeline(nlp_extractors=[detect_greeting])
        result = pipe.run({"score": 1}, input_text="Hello there!")
        assert result.approved is True
        assert result.sanitized_payload.get("greeting") is True
        assert result.nlp_result is not None
        assert len(result.nlp_result.anchors) == 1

    def test_nlp_does_not_overwrite_llm(self):
        def set_x(text, ctx):
            return NLPAnchor(key="x", value=999)

        pipe = InspectionPipeline(nlp_extractors=[set_x])
        result = pipe.run({"x": 42}, input_text="anything")
        assert result.sanitized_payload["x"] == 42  # LLM value preserved

    def test_sanitized_payload_fills_defaults(self):
        schema = {"mode": {"type": "string", "default": "standard"}}
        pipe = InspectionPipeline(turn_input_schema=schema)
        result = pipe.run({})
        assert result.sanitized_payload["mode"] == "standard"

    def test_to_dict_serialisation(self):
        invariants = [
            {"id": "a", "check": "x >= 0", "severity": "warning"},
        ]
        pipe = InspectionPipeline(invariants=invariants)
        result = pipe.run({"x": 5})
        d = result.to_dict()
        assert d["approved"] is True
        assert isinstance(d["violations"], list)
        assert isinstance(d["invariant_summary"], list)
        assert d["invariant_summary"][0]["id"] == "a"
        assert isinstance(d["nlp_anchors"], list)


class TestInspectionResult:
    def test_frozen(self):
        r = InspectionResult(approved=True)
        with pytest.raises(AttributeError):
            r.approved = False  # type: ignore[misc]

    def test_to_dict_empty(self):
        r = InspectionResult(approved=True)
        d = r.to_dict()
        assert d == {
            "approved": True,
            "violations": [],
            "invariant_summary": [],
            "nlp_anchors": [],
        }
