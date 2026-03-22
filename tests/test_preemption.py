"""Tests for lumina.daemon.preemption."""
from __future__ import annotations

import pytest

from lumina.daemon.preemption import PreemptionToken, TaskPreempted


# ── PreemptionToken — no yield requested ──────────────────────────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_checkpoint_passes_when_no_yield() -> None:
    token = PreemptionToken()
    await token.checkpoint()  # should not raise


@pytest.mark.unit
def test_checkpoint_sync_passes_when_no_yield() -> None:
    token = PreemptionToken()
    token.checkpoint_sync()  # should not raise


@pytest.mark.unit
def test_is_yield_requested_initially_false() -> None:
    token = PreemptionToken()
    assert token.is_yield_requested is False


# ── PreemptionToken — yield requested ─────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_checkpoint_raises_when_yield_requested() -> None:
    token = PreemptionToken()
    token.request_yield()
    with pytest.raises(TaskPreempted):
        await token.checkpoint()


@pytest.mark.unit
def test_checkpoint_sync_raises_when_yield_requested() -> None:
    token = PreemptionToken()
    token.request_yield()
    with pytest.raises(TaskPreempted):
        token.checkpoint_sync()


@pytest.mark.unit
def test_is_yield_requested_after_request() -> None:
    token = PreemptionToken()
    token.request_yield()
    assert token.is_yield_requested is True


# ── PreemptionToken — reset ───────────────────────────────────────────────────


@pytest.mark.unit
def test_reset_clears_yield_flag() -> None:
    token = PreemptionToken()
    token.request_yield()
    assert token.is_yield_requested is True
    token.reset()
    assert token.is_yield_requested is False


@pytest.mark.unit
@pytest.mark.anyio
async def test_checkpoint_passes_after_reset() -> None:
    token = PreemptionToken()
    token.request_yield()
    token.reset()
    await token.checkpoint()  # should not raise


# ── TaskPreempted exception ───────────────────────────────────────────────────


@pytest.mark.unit
def test_task_preempted_is_exception() -> None:
    assert issubclass(TaskPreempted, Exception)


@pytest.mark.unit
def test_task_preempted_message() -> None:
    exc = TaskPreempted("test message")
    assert str(exc) == "test message"
