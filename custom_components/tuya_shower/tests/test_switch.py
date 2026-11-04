"""Offline tests for the S1 automatic-mode switch (DP 104)."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from custom_components.tuya_shower.switch import (
    DP_CODE,
    TuyaShowerAutomaticSwitch,
    _read_bool_property,
)


def _properties(value):
    """Create a minimal Tuya shadow response."""
    return {"properties": [{"code": DP_CODE, "value": value}]}


class AutomaticModeParsingTests(unittest.TestCase):
    """Check that unknown Tuya values are never treated as OFF."""

    def test_boolean_representations(self):
        """Accept bool, 0/1 and true/false strings."""
        for raw, expected in (
            (True, True), (False, False), (1, True), (0, False),
            ("true", True), (" TRUE ", True), ("1", True),
            ("false", False), (" FALSE ", False), ("0", False),
        ):
            with self.subTest(raw=raw):
                self.assertIs(_read_bool_property(_properties(raw), DP_CODE), expected)

    def test_unknown_values(self):
        """Reject values whose meaning is ambiguous."""
        for raw in ("on", "off", "yes", "no", 2, None, [], {}):
            with self.subTest(raw=raw):
                self.assertIsNone(_read_bool_property(_properties(raw), DP_CODE))
        self.assertIsNone(_read_bool_property({"properties": []}, DP_CODE))


class AutomaticModeCommandTests(unittest.IsolatedAsyncioTestCase):
    """Verify exact write payload and no automatic write retries."""

    def _entity(self, initial, readbacks=()):
        """Build an entity with a mocked Tuya client."""
        api = Mock()
        replies = [_properties(initial), *[_properties(v) for v in readbacks]]
        api.async_get_device_query_properties = AsyncMock(
            side_effect=[(reply, "ok") for reply in replies]
        )
        api.async_make_request = AsyncMock(return_value={"success": True})
        entity = TuyaShowerAutomaticSwitch("device-test", api)
        entity.async_write_ha_state = Mock()
        return entity, api

    async def test_turn_on_writes_only_dp104(self):
        """ON writes exactly one automatic_mode_switch_1=true command."""
        entity, api = self._entity(False, (True,))
        with patch("custom_components.tuya_shower.switch.asyncio.sleep", new_callable=AsyncMock):
            await entity.async_turn_on()
        api.async_make_request.assert_awaited_once_with(
            "POST",
            "/v1.0/iot-03/devices/device-test/commands",
            body={"commands": [{"code": DP_CODE, "value": True}]},
        )
        self.assertIs(entity.is_on, True)

    async def test_turn_off_writes_only_dp104(self):
        """OFF writes exactly one automatic_mode_switch_1=false command."""
        entity, api = self._entity(True, (False,))
        with patch("custom_components.tuya_shower.switch.asyncio.sleep", new_callable=AsyncMock):
            await entity.async_turn_off()
        api.async_make_request.assert_awaited_once_with(
            "POST",
            "/v1.0/iot-03/devices/device-test/commands",
            body={"commands": [{"code": DP_CODE, "value": False}]},
        )
        self.assertIs(entity.is_on, False)

    async def test_matching_state_skips_post(self):
        """An already matching state must not trigger a write."""
        entity, api = self._entity(True)
        await entity.async_turn_on()
        api.async_make_request.assert_not_awaited()
        self.assertIs(entity.is_on, True)

    async def test_failed_readback_does_not_retry_post(self):
        """Three failed confirmations leave state unknown, without another POST."""
        entity, api = self._entity(False, (False, False, False))
        with patch("custom_components.tuya_shower.switch.asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaisesRegex(RuntimeError, "команда повторно не отправлялась"):
                await entity.async_turn_on()
        api.async_make_request.assert_awaited_once()
        self.assertEqual(api.async_get_device_query_properties.await_count, 4)
        self.assertIsNone(entity.is_on)
        self.assertFalse(entity.available)

    async def test_rejected_post_is_not_retried(self):
        """A rejected write is reported and is not repeated."""
        entity, api = self._entity(False)
        api.async_make_request = AsyncMock(
            return_value={"success": False, "msg": "rejected"}
        )
        with self.assertRaisesRegex(RuntimeError, "отклонила запись"):
            await entity.async_turn_on()
        api.async_make_request.assert_awaited_once()
        self.assertEqual(api.async_get_device_query_properties.await_count, 1)


if __name__ == "__main__":
    unittest.main()
