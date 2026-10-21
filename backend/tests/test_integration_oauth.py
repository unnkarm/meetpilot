"""Offline checks: a failed/unconfigured OAuth exchange must never fake a connection."""
import unittest
import uuid
import json
from unittest.mock import Mock, patch
import httpx
from app.services import google_calendar_service as google, zoom_service as zoom

class IntegrationOAuthTests(unittest.TestCase):
    def test_missing_credentials_never_start_oauth_or_write_connections(self):
        for module, prefix, auth, exchange in [(google, 'GOOGLE', google.get_google_auth_url, google.exchange_google_code), (zoom, 'ZOOM', zoom.get_zoom_auth_url, zoom.exchange_zoom_code)]:
            with self.subTest(provider=prefix), patch.object(module.settings, prefix + '_CLIENT_ID', ''), patch.object(module.settings, prefix + '_CLIENT_SECRET', ''), patch.object(module.httpx, 'post') as post:
                db = Mock()
                with self.assertRaises(ValueError): auth(uuid.uuid4())
                with self.assertRaises(ValueError): exchange(db, uuid.uuid4(), 'code')
                post.assert_not_called()
                db.commit.assert_not_called()

    def test_rejected_or_tokenless_exchange_never_commits(self):
        for module, prefix, exchange in [(google, 'GOOGLE', google.exchange_google_code), (zoom, 'ZOOM', zoom.exchange_zoom_code)]:
            for response in [httpx.Response(400, request=httpx.Request('POST', 'https://example.test/token')), httpx.Response(200, json={}, request=httpx.Request('POST', 'https://example.test/token'))]:
                with self.subTest(provider=prefix, status=response.status_code), patch.object(module.settings, prefix + '_CLIENT_ID', 'configured-id'), patch.object(module.settings, prefix + '_CLIENT_SECRET', 'configured-secret'), patch.object(module.httpx, 'post', return_value=response):
                    db = Mock()
                    with self.assertRaises((ValueError, httpx.HTTPStatusError)): exchange(db, uuid.uuid4(), 'code')
                    db.commit.assert_not_called()

    def test_redirect_override_must_match_server_configuration(self):
        for module, prefix, auth in [(google, 'GOOGLE', google.get_google_auth_url), (zoom, 'ZOOM', zoom.get_zoom_auth_url)]:
            with self.subTest(provider=prefix), patch.object(module.settings, prefix + '_CLIENT_ID', 'id'), patch.object(module.settings, prefix + '_CLIENT_SECRET', 'secret'):
                with self.assertRaises(ValueError): auth(uuid.uuid4(), 'https://untrusted.test/callback')

    def test_valid_exchange_stores_only_provider_tokens_in_encrypted_configuration(self):
        for module, prefix, exchange in [(google, 'GOOGLE', google.exchange_google_code), (zoom, 'ZOOM', zoom.exchange_zoom_code)]:
            token = httpx.Response(200, json={'access_token': 'provider-token', 'refresh_token': 'provider-refresh'}, request=httpx.Request('POST', 'https://example.test/token'))
            profile = httpx.Response(200, json={'email': 'test@example.test', 'first_name': 'Test'}, request=httpx.Request('GET', 'https://example.test/profile'))
            with self.subTest(provider=prefix), patch.object(module.settings, prefix + '_CLIENT_ID', 'id'), patch.object(module.settings, prefix + '_CLIENT_SECRET', 'secret'), patch.object(module.httpx, 'post', return_value=token), patch.object(module.httpx, 'get', return_value=profile), patch.object(module, 'encrypt_secret', return_value='encrypted-payload') as encrypt:
                db = Mock()
                db.query.return_value.filter.return_value.first.return_value = None
                integration = exchange(db, uuid.uuid4(), 'code')
                saved = json.loads(encrypt.call_args.args[0])
                self.assertEqual(saved['access_token'], 'provider-token')
                self.assertEqual(saved['refresh_token'], 'provider-refresh')
                self.assertEqual(integration.encrypted_config, 'encrypted-payload')
                self.assertTrue(integration.is_connected)
                db.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
