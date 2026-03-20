"""Admin auth endpoints — separate login/refresh for admin-tier users.

This router provides air-gapped authentication endpoints for system-level
users (root, domain_authority, it_support).  Tokens issued here carry
``iss: "lumina-admin"`` and ``token_scope: "admin"`` and are signed with
``LUMINA_ADMIN_JWT_SECRET`` when configured.

End-user auth continues to use ``/api/auth/*`` (routes/auth.py).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.concurrency import run_in_threadpool

from lumina.api import config as _cfg
from lumina.api.admin_middleware import (
    _admin_bearer,
    get_admin_user,
    require_admin_auth,
)
from lumina.api.models import LoginRequest, TokenResponse
from lumina.auth.auth import (
    ADMIN_ROLES,
    create_scoped_jwt,
    verify_password,
)

log = logging.getLogger("lumina-api")

router = APIRouter()


@router.post("/api/admin/auth/login", response_model=TokenResponse)
async def admin_login(req: LoginRequest) -> TokenResponse:
    """Authenticate an admin-tier user and issue a scoped admin token."""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = await run_in_threadpool(_cfg.PERSISTENCE.get_user_by_username, req.username)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")

    if user["role"] not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Admin login requires an admin-tier role (root, domain_authority, it_support)",
        )

    token = create_scoped_jwt(
        user_id=user["user_id"],
        role=user["role"],
        governed_modules=user.get("governed_modules") or [],
        domain_roles=user.get("domain_roles") or {},
    )
    return TokenResponse(access_token=token, user_id=user["user_id"], role=user["role"])


@router.post("/api/admin/auth/refresh", response_model=TokenResponse)
async def admin_refresh(
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer),
) -> TokenResponse:
    """Refresh an admin token.  Requires a valid admin-scoped token."""
    current = await get_admin_user(credentials)
    user_data = require_admin_auth(current)

    user = await run_in_threadpool(_cfg.PERSISTENCE.get_user, user_data["sub"])
    if user is None or not user.get("active", True):
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    if user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="User is no longer an admin-tier role")

    token = create_scoped_jwt(
        user_id=user["user_id"],
        role=user["role"],
        governed_modules=user.get("governed_modules") or [],
        domain_roles=user.get("domain_roles") or {},
    )
    return TokenResponse(access_token=token, user_id=user["user_id"], role=user["role"])


@router.get("/api/admin/auth/me")
async def admin_me(
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer),
) -> dict[str, Any]:
    """Return admin profile extracted from a valid admin token."""
    current = await get_admin_user(credentials)
    user_data = require_admin_auth(current)
    return {
        "user_id": user_data["sub"],
        "role": user_data["role"],
        "token_scope": user_data.get("token_scope", "admin"),
        "governed_modules": user_data.get("governed_modules", []),
    }
