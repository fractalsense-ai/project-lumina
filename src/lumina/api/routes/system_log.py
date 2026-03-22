"""System Log query endpoints: records, sessions, single record lookup, warnings, alerts."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.concurrency import run_in_threadpool

from lumina.api import config as _cfg
from lumina.api.middleware import _bearer_scheme, get_current_user, require_auth, require_role
from lumina.system_log.alert_store import warning_store, alert_store

log = logging.getLogger("lumina-api")

router = APIRouter()


@router.get("/api/system-log/records")
async def query_log_records(
    session_id: str | None = None,
    record_type: str | None = None,
    event_type: str | None = None,
    domain_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> list[dict[str, Any]]:
    current = await get_current_user(credentials)
    user_data = require_auth(current)

    allowed_roles = ("root", "qa", "auditor")
    if user_data["role"] not in allowed_roles:
        if user_data["role"] == "domain_authority":
            pass
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    records = await run_in_threadpool(
        _cfg.PERSISTENCE.query_log_records,
        session_id=session_id,
        record_type=record_type,
        event_type=event_type,
        domain_id=domain_id,
        limit=limit,
        offset=offset,
    )
    return records


@router.get("/api/system-log/sessions")
async def list_log_sessions(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> list[dict[str, Any]]:
    current = await get_current_user(credentials)
    user_data = require_auth(current)

    allowed_roles = ("root", "domain_authority", "it_support", "qa", "auditor")
    if user_data["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    summaries = await run_in_threadpool(_cfg.PERSISTENCE.list_log_sessions_summary)
    return summaries


@router.get("/api/system-log/records/{record_id}")
async def get_log_record(
    record_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    current = await get_current_user(credentials)
    user_data = require_auth(current)

    allowed_roles = ("root", "qa", "auditor")
    if user_data["role"] not in allowed_roles:
        if user_data["role"] == "domain_authority":
            pass
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    all_records = await run_in_threadpool(_cfg.PERSISTENCE.query_log_records, limit=10000)
    for r in all_records:
        if r.get("record_id") == record_id:
            return r

    raise HTTPException(status_code=404, detail="Record not found")


@router.get("/api/system-log/warnings")
async def query_warnings(
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> list[dict[str, Any]]:
    """Return recent WARNING-level events from the micro-router dashboard queue."""
    current = await get_current_user(credentials)
    user_data = require_auth(current)

    allowed_roles = ("root", "it_support", "domain_authority", "qa", "auditor")
    if user_data["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return warning_store.query(limit=limit, offset=offset, category_filter=category)


@router.get("/api/system-log/alerts")
async def query_alerts(
    limit: int = 20,
    offset: int = 0,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> list[dict[str, Any]]:
    """Return recent ERROR / CRITICAL events from the micro-router alert stream."""
    current = await get_current_user(credentials)
    user_data = require_auth(current)

    allowed_roles = ("root", "it_support", "domain_authority", "qa", "auditor")
    if user_data["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return alert_store.query(limit=limit, offset=offset)
