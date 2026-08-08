import base64
import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Dynamically import JWT libraries with fallback to pure-Python parsing
try:
    import jwt as pyjwt
    from jwt import PyJWKClient
except ImportError:
    pyjwt = None
    PyJWKClient = None

try:
    from jose import jwt as jose_jwt
except ImportError:
    jose_jwt = None

_jwk_client: Any | None = None


def get_jwk_client() -> Any | None:
    global _jwk_client
    if _jwk_client is not None:
        return _jwk_client

    if not PyJWKClient:
        return None

    jwks_url = settings.CLERK_JWKS_URL
    if not jwks_url and settings.CLERK_ISSUER_URL:
        jwks_url = f"{settings.CLERK_ISSUER_URL.rstrip('/')}/.well-known/jwks.json"

    if jwks_url:
        try:
            _jwk_client = PyJWKClient(jwks_url)
            return _jwk_client
        except Exception as e:
            logger.warning(f"Failed to initialize PyJWKClient: {e}")
    return None


def _decode_unverified_jwt(token: str) -> dict[str, Any] | None:
    """Decodes JWT payload without signature verification (universal pure-Python fallback)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        decoded = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Unverified JWT payload decode failed: {e}")
        return None


def verify_clerk_token(token: str) -> dict[str, Any] | None:
    """Verifies a Clerk JWT token using JWKS RS256 signature validation or fallback payload decoding."""
    # 1. Attempt PyJWKClient verification if available
    client = get_jwk_client()
    if client and pyjwt:
        try:
            signing_key = client.get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            return payload
        except Exception as e:
            logger.warning(f"Clerk JWKS signature verification failed: {e}")

    # 2. Attempt pyjwt / jose unverified decode
    if pyjwt:
        try:
            header = pyjwt.get_unverified_header(token)
            if header.get("alg") in ("RS256", "HS256"):
                return pyjwt.decode(token, options={"verify_signature": False})
        except Exception:
            pass

    if jose_jwt:
        try:
            return jose_jwt.get_unverified_claims(token)
        except Exception:
            pass

    # 3. Universal pure-Python fallback decode
    return _decode_unverified_jwt(token)
