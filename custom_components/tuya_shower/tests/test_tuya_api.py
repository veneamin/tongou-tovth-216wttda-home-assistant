"""Offline unit tests for Tuya Cloud request signing; no network or device access."""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest

from custom_components.tuya_shower.tuya_api import TuyaCloudClient


class TuyaCloudClientSigningTests(unittest.TestCase):
    """Verify request-body serialization and HMAC input."""

    def setUp(self) -> None:
        """Build a client without creating an HTTP session."""
        self.client = TuyaCloudClient.__new__(TuyaCloudClient)
        self.client._client_id = "test-client-id"
        self.client._secret = "test-secret"
        self.client._access_token = "test-access-token"

    def test_body_is_compact_json_and_utf8(self) -> None:
        """JSON sent to Tuya must be compact and encoded as UTF-8."""
        body = {"commands": [{"code": "temp_set", "value": 21}], "label": "душ"}
        expected = json.dumps(
            body, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(TuyaCloudClient._body_bytes(body), expected)

    def test_empty_and_string_bodies(self) -> None:
        """Empty and already serialized bodies must remain unchanged."""
        self.assertEqual(TuyaCloudClient._body_bytes(None), b"")
        self.assertEqual(
            TuyaCloudClient._body_bytes('{"value":1}'), b'{"value":1}'
        )

    def test_business_request_signature(self) -> None:
        """Business API signature includes the access token and real newlines."""
        method = "POST"
        path = "/v1.0/iot-03/devices/device-test/commands"
        timestamp = "1760000000123"
        body = b'{"commands":[{"code":"temp_set","value":21}]}'
        content_hash = hashlib.sha256(body).hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{path}"
        message = (
            "test-client-id"
            "test-access-token"
            f"{timestamp}{string_to_sign}"
        )
        expected = hmac.new(
            b"test-secret", message.encode("utf-8"), hashlib.sha256
        ).hexdigest().upper()

        actual = self.client._signature(
            method, path, timestamp, body, token_request=False
        )
        self.assertEqual(actual, expected)

    def test_token_request_signature(self) -> None:
        """Token endpoint signature must not include an access token."""
        method = "GET"
        path = "/v1.0/token?grant_type=1"
        timestamp = "1760000000456"
        body = b""
        content_hash = hashlib.sha256(body).hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{path}"
        message = f"test-client-id{timestamp}{string_to_sign}"
        expected = hmac.new(
            b"test-secret", message.encode("utf-8"), hashlib.sha256
        ).hexdigest().upper()

        actual = self.client._signature(
            method, path, timestamp, body, token_request=True
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
