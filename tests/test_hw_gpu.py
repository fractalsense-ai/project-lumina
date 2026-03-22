"""Tests for lumina.systools.hw_gpu."""
from __future__ import annotations

import pytest

from lumina.systools.hw_gpu import get_gpu_usage


@pytest.mark.unit
def test_gpu_stub_returns_none() -> None:
    assert get_gpu_usage() is None
