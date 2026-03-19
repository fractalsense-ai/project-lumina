"""Optional SMTP helper for sending invite emails.

All configuration is via environment variables.  If ``LUMINA_SMTP_HOST`` is
not set, the module is considered unconfigured and ``send_invite_email``
returns ``(False, None)`` immediately without attempting a connection.

Required env vars (when SMTP is enabled):
    LUMINA_SMTP_HOST        — SMTP server hostname
    LUMINA_SMTP_PORT        — port (default: 587)
    LUMINA_SMTP_USER        — login username
    LUMINA_SMTP_PASSWORD    — login password
    LUMINA_SMTP_FROM        — envelope from address (default: noreply@lumina)

Used to construct the setup URL:
    LUMINA_BASE_URL         — base URL of the deployment (default: empty string)

``send_invite_email`` never raises — any exception is caught and returned as
the second tuple element so the caller can decide how to surface it.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger("lumina-api")

_SMTP_HOST: str = os.environ.get("LUMINA_SMTP_HOST", "")
_SMTP_PORT: int = int(os.environ.get("LUMINA_SMTP_PORT", "587"))
_SMTP_USER: str = os.environ.get("LUMINA_SMTP_USER", "")
_SMTP_PASSWORD: str = os.environ.get("LUMINA_SMTP_PASSWORD", "")
_SMTP_FROM: str = os.environ.get("LUMINA_SMTP_FROM", "noreply@lumina")


def _smtp_configured() -> bool:
    """Return True only when LUMINA_SMTP_HOST is set (non-empty)."""
    return bool(os.environ.get("LUMINA_SMTP_HOST", "").strip())


def send_invite_email(
    to_address: str,
    username: str,
    setup_url: str,
) -> tuple[bool, str | None]:
    """Send an account-setup invite email to *to_address*.

    Returns ``(True, None)`` on success.
    Returns ``(False, None)`` when SMTP is not configured (silent skip).
    Returns ``(False, error_message)`` when SMTP is configured but delivery fails.
    """
    if not _smtp_configured():
        return False, None

    # Re-read env vars at call time so tests can patch them
    smtp_host = os.environ.get("LUMINA_SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("LUMINA_SMTP_PORT", "587"))
    smtp_user = os.environ.get("LUMINA_SMTP_USER", "")
    smtp_password = os.environ.get("LUMINA_SMTP_PASSWORD", "")
    smtp_from = os.environ.get("LUMINA_SMTP_FROM", "noreply@lumina")

    subject = "Your Lumina account setup"
    body = (
        f"Hello {username},\n\n"
        "Your Lumina account has been created.  "
        "Please follow the link below to set your password and activate your account:\n\n"
        f"  {setup_url}\n\n"
        "This link will expire in 24 hours.  "
        "If you did not request this account, please contact your administrator.\n\n"
        "— The Lumina System"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_address], msg.as_string())
        log.info("Invite email sent to %s", to_address)
        return True, None
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        log.warning("Failed to send invite email to %s: %s", to_address, err)
        return False, err
