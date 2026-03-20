"""NLP pre-processing interface for the Inspection Middleware.

Defines the contract and reusable primitives for Phase A NLP
pre-processing — deterministic signal extraction that runs *before*
the LLM generates its response.

Domain packs compose these primitives in their ``runtime_adapters.py``
to build domain-specific NLP extractors.  The primitives here are
domain-agnostic: keyword matchers, regex extractors, and overlap
calculators that any domain can use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class NLPAnchor:
    """A single deterministic signal extracted from raw input text."""

    key: str
    value: Any
    source: str = "nlp_preprocessor"
    description: str = ""


@dataclass
class NLPPreprocessResult:
    """Aggregated result of NLP pre-processing on a single input turn."""

    anchors: list[NLPAnchor] = field(default_factory=list)
    evidence_partial: dict[str, Any] = field(default_factory=dict)
    anchor_summary: str = ""

    def merge_into(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *evidence* with NLP-extracted fields merged in.

        NLP anchors do **not** override fields already present in
        *evidence* — LLM/tool-adapter values take precedence.
        """
        merged = dict(evidence)
        for key, value in self.evidence_partial.items():
            if key not in merged:
                merged[key] = value
        return merged


# ─────────────────────────────────────────────────────────────
# Reusable NLP primitives
# ─────────────────────────────────────────────────────────────

def keyword_match(
    text: str,
    keywords: list[str],
    *,
    case_sensitive: bool = False,
) -> bool:
    """Return ``True`` if any keyword appears in *text*."""
    if not case_sensitive:
        text = text.lower()
        keywords = [k.lower() for k in keywords]
    return any(kw in text for kw in keywords)


def regex_extract(
    text: str,
    pattern: str,
    *,
    group: int = 0,
    flags: int = re.IGNORECASE,
) -> str | None:
    """Return the first regex match (or a specific group), or ``None``."""
    m = re.search(pattern, text, flags)
    if m is None:
        return None
    try:
        return m.group(group)
    except IndexError:
        return m.group(0)


def vocab_overlap_ratio(
    text: str,
    vocab: set[str],
    *,
    case_sensitive: bool = False,
) -> float:
    """Return the fraction of words in *text* that appear in *vocab*.

    A ratio of 0.0 means no overlap; 1.0 means every word matches.
    """
    if not case_sensitive:
        text = text.lower()
        vocab = {v.lower() for v in vocab}
    words = re.findall(r"\w+", text)
    if not words:
        return 0.0
    return sum(1 for w in words if w in vocab) / len(words)


def caps_ratio(text: str) -> float:
    """Return the fraction of alphabetic characters that are uppercase."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    return sum(1 for c in alpha if c.isupper()) / len(alpha)


def punctuation_density(text: str) -> float:
    """Return the fraction of characters that are punctuation marks."""
    if not text:
        return 0.0
    punct = sum(1 for c in text if c in "!?.,;:…—–-")
    return punct / len(text)


# ─────────────────────────────────────────────────────────────
# Composable extractor type
# ─────────────────────────────────────────────────────────────

NLPExtractorFn = Callable[[str, dict[str, Any]], NLPAnchor | None]
"""Signature for domain-specific NLP extractor functions.

Takes (input_text, task_context) and returns an NLPAnchor if a
signal is detected, or None.
"""


def run_extractors(
    input_text: str,
    task_context: dict[str, Any],
    extractors: list[NLPExtractorFn],
) -> NLPPreprocessResult:
    """Run a list of extractor functions and aggregate results."""
    result = NLPPreprocessResult()
    for extractor_fn in extractors:
        anchor = extractor_fn(input_text, task_context)
        if anchor is not None:
            result.anchors.append(anchor)
            result.evidence_partial[anchor.key] = anchor.value
    if result.anchors:
        parts = [f"{a.key}={a.value!r}" for a in result.anchors]
        result.anchor_summary = "NLP signals: " + ", ".join(parts)
    return result
