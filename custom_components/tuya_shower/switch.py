"""Управление автоматическим режимом S1 душевого терморегулятора.

Единственная записываемая сущность — DP 104 automatic_mode_switch_1.
Она включает/выключает автоматическое регулирование S1. Переключатель
канала DP 2, выбор режима DP 107 и оба температурных порога не изменяются.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from . import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_USER_ID,
    get_cloud_credentials,
)
from .sensor import _properties_to_dict
from .tuya_api import TuyaCloudClient

_LOGGER = logging.getLogger(__name__)

# Опрос состояния — только чтение; запись выполняется только по действию пользователя.
SCAN_INTERVAL = timedelta(seconds=30)
DP_CODE = "automatic_mode_switch_1"
DP_ID = 104

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_CLIENT_ID): cv.string,
        vol.Optional(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_USER_ID): cv.string,
        vol.Optional(CONF_REGION): cv.string,
    }
)


def _read_bool_property(result: Any, code: str) -> bool | None:
    """Вернуть строгое boolean-значение DP; неизвестные значения не угадывать."""
    try:
        value = _properties_to_dict(result).get(code)
    except (AttributeError, TypeError, ValueError):
        return None

    if isinstance(value, bool):
        return value
    # Tuya иногда сериализует boolean как 0/1 или строки true/false.
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
    return None


async def async_setup_platform(
    hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None
) -> None:
    """Создать переключатель DP104 и запустить периодическое чтение."""
    credentials = get_cloud_credentials(hass, config)
    if credentials is None:
        return

    api = TuyaCloudClient(
        hass=hass,
        region_code=credentials["region"],
        client_id=credentials["client_id"],
        secret=credentials["client_secret"],
        user_id=credentials["user_id"],
    )
    entity = TuyaShowerAutomaticSwitch(config[CONF_DEVICE_ID], api)
    async_add_entities([entity])

    # Первый запрос выполняется сразу, затем состояние обновляется каждые 30 секунд.
    await entity.async_refresh_value()

    async def async_update(_now=None) -> None:
        await entity.async_refresh_value()

    async_track_time_interval(hass, async_update, SCAN_INTERVAL)


class TuyaShowerAutomaticSwitch(SwitchEntity):
    """Переключатель разрешения автоматического температурного режима S1."""

    _attr_should_poll = False
    _attr_icon = "mdi:thermostat-auto"

    def __init__(self, device_id: str, api: TuyaCloudClient) -> None:
        """Сохранить ID устройства и общий клиент Tuya Cloud."""
        self._device_id = device_id
        self._api = api
        self._is_on: bool | None = None
        self._write_lock = asyncio.Lock()
        self._attr_name = "ТП душевой — автоматический режим S1"
        self._attr_unique_id = f"{device_id}_s1_automatic_mode"

    @property
    def is_on(self) -> bool | None:
        """Последнее подтверждённое состояние DP104."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Не показывать неизвестное состояние как выключенное."""
        return self._is_on is not None

    async def async_refresh_value(self) -> None:
        """Прочитать DP104 из Tuya Cloud без отправки команд."""
        try:
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError(f"Ошибка чтения DP {DP_ID}: {status}")
            value = _read_bool_property(result, DP_CODE)
            if value is None:
                raise ValueError(f"Tuya не вернула корректное boolean-значение {DP_CODE}")
            self._is_on = value
            self.async_write_ha_state()
        except Exception:
            # При ошибке чтения не подменяем последнее состояние на OFF.
            _LOGGER.exception("Tuya Shower: не удалось прочитать DP %s", DP_ID)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Разрешить автоматический режим S1 и подтвердить DP104 чтением."""
        await self._async_set_automatic_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Запретить автоматический режим S1; это отключает нагревательный выход."""
        await self._async_set_automatic_mode(False)

    async def _async_set_automatic_mode(self, enabled: bool) -> None:
        """Отправить одну команду DP104 и повторять только чтение для проверки."""
        async with self._write_lock:
            # Не посылаем команду, если Tuya не подтверждает исходное состояние.
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError("Не удалось прочитать исходное состояние DP104")
            current = _read_bool_property(result, DP_CODE)
            if current is None:
                raise RuntimeError("Tuya не вернула исходное состояние DP104")
            if current == enabled:
                self._is_on = current
                self.async_write_ha_state()
                return

            # В теле присутствует только DP104. Другие режимы, канал и пороги
            # этим действием не затрагиваются.
            response = await self._api.async_make_request(
                "POST",
                f"/v1.0/iot-03/devices/{self._device_id}/commands",
                body={"commands": [{"code": DP_CODE, "value": enabled}]},
            )
            if not isinstance(response, dict) or not response.get("success"):
                message = (
                    response.get("msg", "неизвестная ошибка")
                    if isinstance(response, dict)
                    else "нет ответа от Tuya"
                )
                raise RuntimeError(f"Tuya отклонила запись DP {DP_ID}: {message}")

            # После POST команду повторно не отправляем. До трёх раз выполняем GET.
            for attempt in range(1, 4):
                await asyncio.sleep(2)
                result, status = await self._api.async_get_device_query_properties(
                    self._device_id
                )
                if status != "ok":
                    _LOGGER.warning(
                        "Tuya Shower: readback DP %s, попытка %s/3: %s",
                        DP_ID, attempt, status,
                    )
                    continue
                actual = _read_bool_property(result, DP_CODE)
                if actual is enabled:
                    self._is_on = actual
                    self.async_write_ha_state()
                    return

            # Итог неизвестен: актуальное значение не выдумываем и команду не повторяем.
            self._is_on = None
            self.async_write_ha_state()
            raise RuntimeError(
                f"Tuya не подтвердила DP {DP_ID}={enabled}; "
                "команда повторно не отправлялась"
            )
