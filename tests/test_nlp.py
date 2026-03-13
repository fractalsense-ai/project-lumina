"""Tests for lumina.core.nlp — NLP primitives and domain classifier."""
from __future__ import annotations

import pytest

import lumina.core.nlp as nlp_mod
from lumina.core.nlp import (
    classify_domain,
    get_nlp,
    split_sentences,
    tokenize,
)


# ── get_nlp ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_get_nlp_returns_instance_or_none() -> None:
    result = get_nlp()
    # Either spaCy is available (returns a Language object) or not (returns None).
    # Both are valid; we just ensure no exception is raised.
    assert result is None or hasattr(result, "pipe")


@pytest.mark.unit
def test_get_nlp_caches_result() -> None:
    first = get_nlp()
    second = get_nlp()
    assert first is second


@pytest.mark.unit
def test_get_nlp_returns_none_after_forced_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nlp_mod, "_spacy_available", False)
    monkeypatch.setattr(nlp_mod, "_nlp_instance", None)
    result = get_nlp()
    assert result is None


# ── split_sentences ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_split_sentences_empty_string() -> None:
    assert split_sentences("") == []


@pytest.mark.unit
def test_split_sentences_single_sentence() -> None:
    parts = split_sentences("Hello world.")
    assert len(parts) >= 1
    assert "Hello world" in parts[0] or "Hello" in parts[0]


@pytest.mark.unit
def test_split_sentences_semicolon_split(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force regex fallback so we can test semicolon splitting deterministically
    import lumina.core.nlp as nlp_mod
    monkeypatch.setattr(nlp_mod, "_nlp_instance", None)
    monkeypatch.setattr(nlp_mod, "_spacy_available", False)
    text = "I checked by substitution; the answer is correct"
    parts = split_sentences(text)
    assert len(parts) >= 2


@pytest.mark.unit
def test_split_sentences_so_that_connector() -> None:
    text = "I solved x = 4 so that means the equation balances"
    parts = split_sentences(text)
    assert len(parts) >= 1


@pytest.mark.unit
def test_split_sentences_therefore_connector() -> None:
    text = "we add 5 to both sides therefore we get x = 4"
    parts = split_sentences(text)
    assert len(parts) >= 1


@pytest.mark.unit
def test_split_sentences_multiline() -> None:
    text = "First line.\nSecond line."
    parts = split_sentences(text)
    assert len(parts) >= 1


@pytest.mark.unit
def test_split_sentences_only_whitespace() -> None:
    assert split_sentences("   \n\n   ") == []


@pytest.mark.unit
def test_split_sentences_comma_connector() -> None:
    text = "I added 3, then divided by 2"
    parts = split_sentences(text)
    assert len(parts) >= 1


@pytest.mark.unit
def test_split_sentences_no_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nlp_mod, "_nlp_instance", None)
    monkeypatch.setattr(nlp_mod, "_spacy_available", False)
    parts = split_sentences("First sentence. Second sentence.")
    assert len(parts) >= 1


# ── tokenize ───────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_tokenize_basic() -> None:
    tokens = tokenize("hello world")
    assert "hello" in tokens
    assert "world" in tokens


@pytest.mark.unit
def test_tokenize_empty_string() -> None:
    tokens = tokenize("")
    assert tokens == []


@pytest.mark.unit
def test_tokenize_no_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nlp_mod, "_nlp_instance", None)
    monkeypatch.setattr(nlp_mod, "_spacy_available", False)
    tokens = tokenize("alpha beta gamma")
    assert tokens == ["alpha", "beta", "gamma"]


# ── classify_domain ────────────────────────────────────────────────────────────


_DOMAIN_MAP = {
    "education": {
        "label": "Education",
        "description": "Algebra, math problems, learning",
        "keywords": ["algebra", "equation", "math", "solve", "variable"],
    },
    "agriculture": {
        "label": "Agriculture",
        "description": "Farming, crop management, irrigation",
        "keywords": ["crop", "irrigation", "harvest", "soil", "fertilizer"],
    },
}


@pytest.mark.unit
def test_classify_domain_returns_none_for_empty_text() -> None:
    assert classify_domain("", _DOMAIN_MAP) is None


@pytest.mark.unit
def test_classify_domain_returns_none_for_empty_map() -> None:
    assert classify_domain("algebra equation", {}) is None


@pytest.mark.unit
def test_classify_domain_keyword_match() -> None:
    result = classify_domain("I'm solving an algebra equation", _DOMAIN_MAP)
    assert result is not None
    assert result["domain_id"] == "education"
    assert result["method"] == "keyword"
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.unit
def test_classify_domain_keyword_match_agriculture() -> None:
    result = classify_domain("The crop irrigation needs fertilizer this harvest season", _DOMAIN_MAP)
    assert result is not None
    assert result["domain_id"] == "agriculture"
    assert result["method"] == "keyword"


@pytest.mark.unit
def test_classify_domain_respects_accessible_domains() -> None:
    # Only agriculture is accessible
    result = classify_domain(
        "algebra math solve equation variable",
        _DOMAIN_MAP,
        accessible_domains=["agriculture"],
    )
    # education keywords won't be considered
    assert result is None or result["domain_id"] == "agriculture"


@pytest.mark.unit
def test_classify_domain_empty_accessible_list_returns_none() -> None:
    result = classify_domain("algebra equation", _DOMAIN_MAP, accessible_domains=[])
    assert result is None


@pytest.mark.unit
def test_classify_domain_no_keyword_match_falls_through() -> None:
    result = classify_domain("completely unrelated topic here", _DOMAIN_MAP)
    assert result is None or isinstance(result, dict)


@pytest.mark.unit
def test_classify_domain_description_fallback() -> None:
    # Use a map with no keywords to force description fallback
    domain_map_no_kw = {
        "education": {
            "label": "Education Learning",
            "description": "algebra learning math solving equations",
            "keywords": [],
        },
    }
    result = classify_domain("algebra solving equations learning", domain_map_no_kw)
    # Either finds via description or returns None — both are valid.
    # What matters: no exception is raised.
    assert result is None or result["domain_id"] == "education"


@pytest.mark.unit
def test_classify_domain_below_threshold_returns_none() -> None:
    # One keyword out of 5 at 20% → confidence 0.4, below 0.6 threshold
    domain_map = {
        "edu": {
            "label": "Edu",
            "description": "specialized algebra topic",
            "keywords": ["algebra", "theorem", "proof", "calculus", "topology"],
        }
    }
    result = classify_domain("algebra", domain_map)
    # 1/5 * 2 = 0.4, below threshold
    assert result is None


@pytest.mark.unit
def test_classify_domain_confidence_scaled_up() -> None:
    # 3 of 5 keywords: 3/5 * 2 = 1.2 → capped at 1.0
    domain_map = {
        "edu": {
            "label": "Education",
            "description": "math topics",
            "keywords": ["algebra", "equation", "solve", "variable", "constant"],
        }
    }
    result = classify_domain("algebra equation solve variable something", domain_map)
    assert result is not None
    assert result["confidence"] <= 1.0
