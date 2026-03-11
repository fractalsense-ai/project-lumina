"""Shared NLP utilities for the education domain.

Provides a lazy-loading spaCy interface that caches the model globally
and degrades gracefully when spaCy or the language model is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("edu_nlp_utils")

_nlp_instance: Any = None
_spacy_available: bool | None = None


def get_nlp() -> Any | None:
    """Return a cached spaCy Language instance, or None if unavailable.

    Loads ``en_core_web_sm`` on first call and caches it globally.
    Returns None (no exception) when spaCy is not installed or the
    model has not been downloaded.
    """
    global _nlp_instance, _spacy_available

    if _spacy_available is False:
        return None
    if _nlp_instance is not None:
        return _nlp_instance

    try:
        import spacy
        _nlp_instance = spacy.load("en_core_web_sm")
        _spacy_available = True
        log.info("spaCy model en_core_web_sm loaded successfully")
        return _nlp_instance
    except ImportError:
        _spacy_available = False
        log.info("spaCy not installed — falling back to regex-based NLP")
        return None
    except OSError:
        _spacy_available = False
        log.info("spaCy model en_core_web_sm not found — falling back to regex-based NLP")
        return None


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using spaCy, with regex fallback.

    Returns a list of non-empty sentence strings.
    """
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if sentences:
            return sentences

    # Regex fallback: split on sentence-ending punctuation followed by
    # whitespace, or on natural-language connectors used between algebraic
    # steps.  Avoids splitting on periods inside decimals.
    import re
    parts: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        # Split on natural-language step connectors
        fragments = re.split(
            r"[;,]\s*(?=[A-Za-z])"            # semicolons / commas before words
            r"|(?<=\d)\.\s+(?=[A-Z])"          # period-space after digit before capital
            r"|(?<=[a-z])\.\s+(?=[A-Z])"       # period-space after lowercase before capital
            r"|\bso\s+that\s+(?:means?\s+)?"   # "so that means"
            r"|\bso\b\s+"                      # "so "
            r"|\bthen\b\s+"                    # "then "
            r"|\bmeaning\b\s+"                 # "meaning "
            r"|\btherefore\b\s+"               # "therefore "
            r"|\bafter\s+(?:that\s+)?"         # "after that"
            r"|\bwhich\s+means\b\s+"           # "which means"
            r"|\bnow\b\s+",                    # "now "
            stripped,
            flags=re.IGNORECASE,
        )
        for part in fragments:
            part = part.strip()
            if part:
                parts.append(part)
    return parts
