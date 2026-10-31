"""Shared setup and credential handling for Tuya Shower.

Credentials can be supplied directly in the YAML platform configuration.
For backward compatibility, an existing LocalTuya config entry can still
provide credentials when no explicit Tuya Shower credentials are configured.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

DOMAIN = "tuya_shower"
_LOGGER = logging.getLogger(__name__)

# Keep these names aligned with the YAML options documented in README.md.
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_USER_ID = "user_id"
CONF_REGION = "region"
CREDENTIAL_KEYS = (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_USER_ID,
    CONF_REGION,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialize integration storage."""
    hass.data.setdefault(DOMAIN, {})
    return True


def get_cloud_credentials(hass: HomeAssistant, platform_config: dict) -> dict[str, str] | None:
    """Return Tuya Cloud credentials from YAML or legacy LocalTuya storage.

    Explicit Tuya Shower settings take precedence. A partially configured set
    is rejected rather than silently falling back to another credential set.
    LocalTuya is consulted only when none of the four explicit values exists.
    """
    explicit_values = {
        key: platform_config.get(key)
        for key in CREDENTIAL_KEYS
    }
    if any(value is not None for value in explicit_values.values()):
        missing = [key for key, value in explicit_values.items() if not value]
        if missing:
            _LOGGER.error(
                "Tuya Shower: incomplete YAML credentials; missing: %s",
                ", ".join(missing),
            )
            return None
        return {key: str(value) for key, value in explicit_values.items()}

    # Backward compatibility: reuse existing LocalTuya credentials without
    # importing or depending on LocalTuya's internal Python API.
    entries = hass.config_entries.async_entries("localtuya")
    if not entries:
        _LOGGER.error(
            "Tuya Shower: configure client_id, client_secret, user_id and region "
            "in YAML, or provide an existing LocalTuya config entry"
        )
        return None

    stored_values: dict[str, Any] = entries[0].data
    if any(not stored_values.get(key) for key in CREDENTIAL_KEYS):
        _LOGGER.error("Tuya Shower: LocalTuya cloud credentials are incomplete")
        return None

    _LOGGER.warning(
        "Tuya Shower: using credentials from LocalTuya for backward compatibility; "
        "move them to the Tuya Shower YAML configuration when convenient"
    )
    return {key: str(stored_values[key]) for key in CREDENTIAL_KEYS}
