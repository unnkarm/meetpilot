import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet_key() -> bytes:
    """Derives a valid 32-byte URL-safe base64 key for Fernet symmetric encryption."""
    raw = (settings.ENCRYPTION_SECRET_KEY or settings.JWT_SECRET_KEY or "fallback-secret-meetpilot-32-chars").encode("utf-8")
    derived = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(derived)


def encrypt_secret(plain_text: str) -> str:
    """Encrypts a plaintext secret (webhook URL, OAuth token) for storage at rest."""
    if not plain_text:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return plain_text


def decrypt_secret(encrypted_text: str) -> str:
    """Decrypts an encrypted secret."""
    if not encrypted_text:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted_text


def mask_secret(secret_text: str, provider: str = "") -> str:
    """Returns a safe masked representation of the secret for UI display."""
    if not secret_text:
        return "Not Connected"
    if provider == "discord" or secret_text.startswith("http"):
        # e.g., https://discord.com/api/webhooks/12345/abc... -> https://discord.com/api/webhooks/12345/***
        parts = secret_text.split("/")
        if len(parts) > 6:
            return f"{'/'.join(parts[:6])}/***"
        return secret_text[:25] + "***"
    if "@" in secret_text:
        # e.g. subham@gmail.com -> s***m@gmail.com
        user, domain = secret_text.split("@", 1)
        if len(user) > 2:
            return f"{user[0]}***{user[-1]}@{domain}"
        return f"{user[:1]}***@{domain}"
    return f"{secret_text[:4]}***"
