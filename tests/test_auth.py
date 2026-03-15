from __future__ import annotations

import time

import pytest

from lumina.auth import auth


@pytest.mark.unit
def test_hash_and_verify_password_roundtrip() -> None:
    stored = auth.hash_password("S3curePass!")
    assert auth.verify_password("S3curePass!", stored)
    assert not auth.verify_password("wrong-pass", stored)


@pytest.mark.unit
def test_verify_password_rejects_malformed_storage() -> None:
    assert not auth.verify_password("anything", "not-a-salt-hash")


# ---------------------------------------------------------------------------
# Multi-algorithm password hashing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hash_sha256_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """SHA-256 path works when explicitly selected."""
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "sha256")
    stored = auth.hash_password("testpass")
    assert ":" in stored
    assert not stored.startswith("$")
    assert auth.verify_password("testpass", stored)
    assert not auth.verify_password("wrong", stored)


@pytest.mark.unit
def test_hash_bcrypt_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt path works when installed and selected."""
    pytest.importorskip("bcrypt")
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "bcrypt")
    stored = auth.hash_password("testpass")
    assert stored.startswith("$2b$")
    assert auth.verify_password("testpass", stored)
    assert not auth.verify_password("wrong", stored)


@pytest.mark.unit
def test_hash_argon2id_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Argon2id path works when installed and selected."""
    pytest.importorskip("argon2")
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "argon2id")
    stored = auth.hash_password("testpass")
    assert stored.startswith("$argon2id$")
    assert auth.verify_password("testpass", stored)
    assert not auth.verify_password("wrong", stored)


@pytest.mark.unit
def test_detect_algorithm_argon2id() -> None:
    assert auth._detect_algorithm("$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$somehash") == "argon2id"


@pytest.mark.unit
def test_detect_algorithm_bcrypt() -> None:
    assert auth._detect_algorithm("$2b$12$LJ3m4ys6YwdMlT0FQ.8Lh.somebcrypthash") == "bcrypt"


@pytest.mark.unit
def test_detect_algorithm_sha256() -> None:
    assert auth._detect_algorithm("abcdef1234567890:deadbeef") == "sha256"


@pytest.mark.unit
def test_detect_algorithm_unknown() -> None:
    assert auth._detect_algorithm("totally-random-string") == "unknown"


@pytest.mark.unit
def test_verify_password_cross_algorithm(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_password auto-detects even when the configured default differs."""
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "sha256")
    sha_stored = auth.hash_password("cross-test")

    # Switch default to argon2id — verify still works on the SHA-256 hash
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "argon2id")
    assert auth.verify_password("cross-test", sha_stored)


@pytest.mark.unit
def test_fallback_when_all_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When argon2 and bcrypt are unavailable, falls back to sha256."""
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "argon2id")
    monkeypatch.setattr(auth, "_has_argon2", lambda: False)
    monkeypatch.setattr(auth, "_has_bcrypt", lambda: False)
    assert auth._resolve_algorithm() == "sha256"


@pytest.mark.unit
def test_fallback_argon2_to_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """When argon2 is missing but bcrypt is available, falls back to bcrypt."""
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "argon2id")
    monkeypatch.setattr(auth, "_has_argon2", lambda: False)
    monkeypatch.setattr(auth, "_has_bcrypt", lambda: True)
    assert auth._resolve_algorithm() == "bcrypt"


@pytest.mark.unit
def test_fallback_bcrypt_to_sha256(monkeypatch: pytest.MonkeyPatch) -> None:
    """When bcrypt is requested but missing, falls back to sha256."""
    monkeypatch.setattr(auth, "PASSWORD_HASH_ALGORITHM", "bcrypt")
    monkeypatch.setattr(auth, "_has_bcrypt", lambda: False)
    assert auth._resolve_algorithm() == "sha256"


@pytest.mark.unit
def test_verify_returns_false_for_unknown_format() -> None:
    """verify_password returns False for completely unrecognized format."""
    assert not auth.verify_password("anything", "no-recognized-format-here")


@pytest.mark.unit
def test_create_and_verify_jwt_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    token = auth.create_jwt(user_id="u-123", role="user", governed_modules=["mod-1"], ttl_minutes=5)

    payload = auth.verify_jwt(token)
    assert payload["sub"] == "u-123"
    assert payload["role"] == "user"
    assert payload["governed_modules"] == ["mod-1"]
    assert payload["iss"] == auth.JWT_ISSUER


@pytest.mark.unit
def test_create_jwt_rejects_invalid_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    with pytest.raises(ValueError, match="Invalid role"):
        auth.create_jwt(user_id="u-1", role="superuser")


@pytest.mark.unit
def test_create_jwt_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "")
    with pytest.raises(auth.AuthError, match="LUMINA_JWT_SECRET must be set"):
        auth.create_jwt(user_id="u-1", role="user")


@pytest.mark.unit
def test_verify_jwt_rejects_tampered_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    token = auth.create_jwt(user_id="u-1", role="user")
    head, payload, sig = token.split(".")
    tampered = f"{head}.{payload[:-1]}A.{sig}"

    with pytest.raises(auth.TokenInvalidError):
        auth.verify_jwt(tampered)


@pytest.mark.unit
def test_verify_jwt_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    token = auth.create_jwt(user_id="u-1", role="user", ttl_minutes=0)
    time.sleep(1)

    with pytest.raises(auth.TokenExpiredError):
        auth.verify_jwt(token)


@pytest.mark.unit
def test_verify_jwt_rejects_wrong_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    token = auth.create_jwt(user_id="u-1", role="user")

    # Temporarily switch expected issuer to force mismatch.
    monkeypatch.setattr(auth, "JWT_ISSUER", "different-issuer")
    with pytest.raises(auth.TokenInvalidError, match="Unexpected issuer"):
        auth.verify_jwt(token)


@pytest.mark.unit
def test_verify_jwt_rejects_malformed_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")
    with pytest.raises(auth.TokenInvalidError, match="Malformed token"):
        auth.verify_jwt("not.a.valid.jwt.with.extra")
