"""
Project Lumina — JWT Authentication Module

Provides token creation, verification, and password hashing for the
built-in auth service.  Designed for the reference implementation only;
production deployments should evaluate an external IdP.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET: str = os.environ.get("LUMINA_JWT_SECRET", "")
JWT_ALGORITHM: str = os.environ.get("LUMINA_JWT_ALGORITHM", "HS256").upper()
JWT_TTL_MINUTES: int = int(os.environ.get("LUMINA_JWT_TTL_MINUTES", "60"))
JWT_ISSUER: str = "lumina"

# Password hashing — supported values: "argon2id", "bcrypt", "sha256"
PASSWORD_HASH_ALGORITHM: str = os.environ.get(
    "LUMINA_PASSWORD_HASH_ALGORITHM", "argon2id"
).lower()

# Valid Lumina roles (see specs/rbac-spec-v1.md)
VALID_ROLES: frozenset[str] = frozenset(
    {"root", "domain_authority", "it_support", "qa", "auditor", "user", "guest"}
)

# In-memory set of revoked token JTIs.  Cleared on server restart
# (tokens have a TTL so this is acceptable for the reference impl).
_REVOKED_JTIS: set[str] = set()


def revoke_token_jti(jti: str) -> None:
    """Add a JTI to the revocation set."""
    _REVOKED_JTIS.add(jti)


def is_token_revoked(jti: str) -> bool:
    """Check if a JTI has been revoked."""
    return jti in _REVOKED_JTIS


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base exception for authentication/authorization failures."""


class TokenExpiredError(AuthError):
    """Raised when a JWT has expired."""


class TokenInvalidError(AuthError):
    """Raised when a JWT cannot be verified."""


# ---------------------------------------------------------------------------
# Password hashing — multi-algorithm (argon2id, bcrypt, sha256)
# ---------------------------------------------------------------------------


def _has_argon2() -> bool:
    """Return True if argon2-cffi is installed."""
    try:
        import argon2  # noqa: F401
        return True
    except ImportError:
        return False


def _has_bcrypt() -> bool:
    """Return True if the bcrypt package is installed."""
    try:
        import bcrypt  # noqa: F401
        return True
    except ImportError:
        return False


def _resolve_algorithm() -> str:
    """Return the effective hashing algorithm, falling back when libs are missing."""
    algo = PASSWORD_HASH_ALGORITHM
    if algo == "argon2id":
        if _has_argon2():
            return "argon2id"
        if _has_bcrypt():
            log.warning("argon2-cffi not installed; falling back to bcrypt")
            return "bcrypt"
        log.warning(
            "argon2-cffi and bcrypt not installed; falling back to sha256"
        )
        return "sha256"
    if algo == "bcrypt":
        if _has_bcrypt():
            return "bcrypt"
        log.warning("bcrypt not installed; falling back to sha256")
        return "sha256"
    return "sha256"


def _generate_salt(length: int = 32) -> str:
    """Generate a hex-encoded random salt (SHA-256 legacy path only)."""
    return secrets.token_hex(length)


def _hash_sha256(password: str) -> str:
    """SHA-256 + per-user salt.  Returns ``salt:hex_digest``."""
    salt = _generate_salt()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def _hash_bcrypt(password: str) -> str:
    """bcrypt.  Returns the standard ``$2b$...`` string."""
    import bcrypt as _bcrypt

    return _bcrypt.hashpw(
        password.encode("utf-8"),
        _bcrypt.gensalt(rounds=12),
    ).decode("ascii")


def _hash_argon2id(password: str) -> str:
    """Argon2id.  Returns the standard ``$argon2id$...`` string."""
    from argon2 import PasswordHasher
    import argon2 as _argon2

    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=_argon2.Type.ID,
    )
    return ph.hash(password)


def _detect_algorithm(stored: str) -> str:
    """Infer the algorithm from a stored hash string."""
    if stored.startswith("$argon2"):
        return "argon2id"
    if stored.startswith(("$2b$", "$2a$")):
        return "bcrypt"
    if ":" in stored:
        return "sha256"
    return "unknown"


def _verify_sha256(password: str, stored: str) -> bool:
    salt, expected = stored.split(":", 1)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, expected)


def _verify_bcrypt(password: str, stored: str) -> bool:
    import bcrypt as _bcrypt

    return _bcrypt.checkpw(
        password.encode("utf-8"),
        stored.encode("ascii"),
    )


def _verify_argon2id(password: str, stored: str) -> bool:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    ph = PasswordHasher()
    try:
        return ph.verify(stored, password)
    except VerifyMismatchError:
        return False


def hash_password(password: str) -> str:
    """Hash *password* using the configured algorithm.

    Default: Argon2id (configurable via ``LUMINA_PASSWORD_HASH_ALGORITHM``).
    Falls back gracefully when the required library is not installed.
    """
    algo = _resolve_algorithm()
    if algo == "argon2id":
        return _hash_argon2id(password)
    if algo == "bcrypt":
        return _hash_bcrypt(password)
    return _hash_sha256(password)


def verify_password(password: str, stored: str) -> bool:
    """Verify *password* against a stored hash string.

    Auto-detects the hashing algorithm from the stored format:
    Argon2id (``$argon2id$...``), bcrypt (``$2b$...``), or
    SHA-256 legacy (``salt:hash``).
    """
    algo = _detect_algorithm(stored)
    try:
        if algo == "argon2id":
            return _verify_argon2id(password, stored)
        if algo == "bcrypt":
            return _verify_bcrypt(password, stored)
        if algo == "sha256":
            return _verify_sha256(password, stored)
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# Minimal HS256 JWT (no external dependency)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return urlsafe_b64decode(padded)


def _sign_hs256(message: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def create_jwt(
    user_id: str,
    role: str,
    governed_modules: list[str] | None = None,
    ttl_minutes: int | None = None,
) -> str:
    """Create a signed JWT with Lumina claims.

    Parameters
    ----------
    user_id:
        Pseudonymous user identifier (``sub`` claim).
    role:
        One of the six canonical role IDs.
    governed_modules:
        Module IDs this user governs (only meaningful for ``domain_authority``).
    ttl_minutes:
        Token lifetime override.  Falls back to ``LUMINA_JWT_TTL_MINUTES``.

    Returns
    -------
    str
        Encoded JWT string.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role!r}")
    if JWT_ALGORITHM != "HS256":
        raise AuthError(f"Unsupported algorithm: {JWT_ALGORITHM}")
    if not JWT_SECRET:
        raise AuthError(
            "LUMINA_JWT_SECRET must be set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    now = int(time.time())
    ttl = ttl_minutes if ttl_minutes is not None else JWT_TTL_MINUTES

    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "governed_modules": governed_modules or [],
        "iat": now,
        "exp": now + ttl * 60,
        "iss": JWT_ISSUER,
        "jti": secrets.token_hex(16),
    }

    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{h}.{p}".encode("ascii")
    sig = _b64url_encode(_sign_hs256(message, JWT_SECRET))
    return f"{h}.{p}.{sig}"


def verify_jwt(token: str) -> dict[str, Any]:
    """Verify and decode a Lumina JWT.

    Returns the decoded payload dict on success.

    Raises
    ------
    TokenExpiredError
        If the token has expired.
    TokenInvalidError
        If the signature is invalid or the token is malformed.
    """
    if not JWT_SECRET:
        raise AuthError("LUMINA_JWT_SECRET is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise TokenInvalidError("Malformed token")

    h_part, p_part, s_part = parts
    message = f"{h_part}.{p_part}".encode("ascii")

    expected_sig = _sign_hs256(message, JWT_SECRET)
    actual_sig = _b64url_decode(s_part)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise TokenInvalidError("Signature verification failed")

    try:
        payload = json.loads(_b64url_decode(p_part))
    except Exception as exc:
        raise TokenInvalidError(f"Invalid payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise TokenInvalidError("Payload is not a JSON object")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and time.time() > exp:
        raise TokenExpiredError("Token has expired")

    if payload.get("iss") != JWT_ISSUER:
        raise TokenInvalidError(f"Unexpected issuer: {payload.get('iss')!r}")

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise TokenInvalidError("Token has been revoked")

    return payload
