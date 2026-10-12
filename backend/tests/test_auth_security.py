"""Authentication must never accept client-controlled or unsigned identity claims."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.security import get_clerk_issuer, verify_clerk_token


class ClerkVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()
        cls.issuer = "https://example.clerk.accounts.dev"

    def _token(self, **overrides):
        claims = {"sub": "user_a", "iss": self.issuer,
                  "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def test_valid_signed_token(self):
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.public_key))
        with patch("app.core.security.get_jwk_client", return_value=client), \
             patch("app.core.security.settings.CLERK_ISSUER_URL", self.issuer):
            self.assertEqual(verify_clerk_token(self._token())["sub"], "user_a")

    def test_issuer_is_derived_from_configured_frontend_jwks_url(self):
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.public_key))
        with patch("app.core.security.get_jwk_client", return_value=client), \
             patch("app.core.security.settings.CLERK_ISSUER_URL", ""), \
             patch("app.core.security.settings.CLERK_JWKS_URL", self.issuer + "/.well-known/jwks.json"):
            self.assertEqual(get_clerk_issuer(), self.issuer)
            self.assertEqual(verify_clerk_token(self._token())["sub"], "user_a")

    def test_wrong_issuer_and_expired_tokens_fail_closed(self):
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.public_key))
        with patch("app.core.security.get_jwk_client", return_value=client), \
             patch("app.core.security.settings.CLERK_ISSUER_URL", self.issuer):
            self.assertIsNone(verify_clerk_token(self._token(iss="https://attacker.invalid")))
            self.assertIsNone(verify_clerk_token(self._token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))))

    def test_unverified_or_unsigned_token_never_falls_back(self):
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.public_key))
        forged = jwt.encode({"sub": "user_b", "iss": self.issuer,
                             "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                            "attacker-key", algorithm="HS256")
        with patch("app.core.security.get_jwk_client", return_value=client), \
             patch("app.core.security.settings.CLERK_ISSUER_URL", self.issuer):
            self.assertIsNone(verify_clerk_token(forged))
        with patch("app.core.security.get_jwk_client", return_value=None):
            self.assertIsNone(verify_clerk_token(self._token()))
