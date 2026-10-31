"""Tests for Tuya Shower credential selection and legacy compatibility."""
from __future__ import annotations

import unittest
from unittest.mock import Mock

from custom_components.tuya_shower import get_cloud_credentials


class CredentialSelectionTests(unittest.TestCase):
    """Verify explicit YAML credentials and the LocalTuya fallback."""

    def setUp(self) -> None:
        """Prepare a fake Home Assistant object with no LocalTuya entries."""
        self.hass = Mock()
        self.hass.config_entries.async_entries.return_value = []
        self.credentials = {
            "client_id": "yaml-client",
            "client_secret": "yaml-secret",
            "user_id": "yaml-user",
            "region": "eu",
        }

    def test_explicit_yaml_credentials_are_used(self) -> None:
        """Own YAML credentials take precedence and need no LocalTuya entry."""
        result = get_cloud_credentials(self.hass, self.credentials)
        self.assertEqual(result, self.credentials)
        self.hass.config_entries.async_entries.assert_not_called()

    def test_partial_yaml_credentials_are_rejected(self) -> None:
        """A partial explicit set must not silently fall back to LocalTuya."""
        result = get_cloud_credentials(
            self.hass, {"client_id": "yaml-client"}
        )
        self.assertIsNone(result)
        self.hass.config_entries.async_entries.assert_not_called()

    def test_legacy_localtuya_credentials_are_supported(self) -> None:
        """Existing installations continue to work during migration."""
        entry = Mock()
        entry.data = {
            "client_id": "legacy-client",
            "client_secret": "legacy-secret",
            "user_id": "legacy-user",
            "region": "eu",
        }
        self.hass.config_entries.async_entries.return_value = [entry]
        result = get_cloud_credentials(self.hass, {})
        self.assertEqual(result, entry.data)
        self.hass.config_entries.async_entries.assert_called_once_with("localtuya")

    def test_missing_credentials_return_none(self) -> None:
        """Without YAML credentials or LocalTuya, setup must stop cleanly."""
        self.assertIsNone(get_cloud_credentials(self.hass, {}))


if __name__ == "__main__":
    unittest.main()
