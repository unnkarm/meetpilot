"""Fail-closed verification of Clerk session JWTs."""

import logging
from typing import Any
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)
_jwk_client: PyJWKClient | None = None


def get_clerk_issuer() -> str | None:
    """Use the explicit issuer or derive it from Clerk's Frontend API JWKS URL."""
    if settings.CLERK_ISSUER_URL:
        return settings.CLERK_ISSUER_URL.rstrip("/")
    parsed = urlparse(settings.CLERK_JWKS_URL)
    if (parsed.scheme == "https" and parsed.netloc and
            parsed.path == "/.well-known/jwks.json" and
            not parsed.query and not parsed.fragment):
        return f"https://{parsed.netloc}"
    return None


def get_jwk_client() -> PyJWKClient | None:
    global _jwk_client
    if _jwk_client is not None:
        return _jwk_client
    jwks_url = settings.CLERK_JWKS_URL or (
        f"{settings.CLERK_ISSUER_URL.rstrip('/')}/.well-known/jwks.json"
        if settings.CLERK_ISSUER_URL else ""
    )
    if not jwks_url or not jwks_url.startswith("https://"):
        return None
    _jwk_client = PyJWKClient(jwks_url)
    return _jwk_client


def verify_clerk_token(token: str) -> dict[str, Any] | None:
    """Return claims only after RS256 signature, expiry and issuer checks."""
    try:
        client = get_jwk_client()
    except (ValueError, OSError) as exc:
        logger.warning("Clerk verifier initialization failed: %s", type(exc).__name__)
        return None
    issuer = get_clerk_issuer()
    if client is None or issuer is None:
        logger.error("Clerk JWKS URL or issuer cannot be determined")
        return None
    try:
        key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False, "require": ["exp", "iss", "sub"]},
        )
    except (jwt.PyJWTError, ValueError, OSError) as exc:
        logger.warning("Clerk token verification failed: %s", type(exc).__name__)
        return None
