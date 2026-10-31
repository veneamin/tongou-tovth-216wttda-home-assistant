"""Регуляторы температурных порогов S1 контроллера душевой.

Два независимых поля и общий ползунок, сохраняющий текущую ширину диапазона.
При повышении общий ползунок сначала записывает верхний DP 110,
затем нижний DP 22. При понижении — сначала нижний DP 22,
затем верхний DP 110. Реле и режимы не изменяются.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.number import NumberEntity, NumberMode, PLATFORM_SCHEMA
from homeassistant.const import CONF_DEVICE_ID, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from . import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_USER_ID,
    get_cloud_credentials,
)
from .tuya_api import TuyaCloudClient

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_CLIENT_ID): cv.string,
        vol.Optional(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_USER_ID): cv.string,
        vol.Optional(CONF_REGION): cv.string,
    }
)

CONTROLS = (
    {"key": "s1_lower", "name": "ТП душевой — нижний порог S1", "code": "temp_set", "dp_id": 22},
    {"key": "s1_upper", "name": "ТП душевой — верхний порог S1", "code": "temp_set_f_3", "dp_id": 110},
)


def _read_dp_value(result: Any, code: str) -> int | None:
    """Найти значение DP в ответе Tuya и привести его к целому числу."""
    properties = result.get("properties", []) if isinstance(result, dict) else []
    if isinstance(properties, dict):
        value = properties.get(code)
    else:
        value = next(
            (item.get("value") for item in properties
             if isinstance(item, dict) and item.get("code") == code),
            None,
        )
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _async_write_dp_and_confirm(
    api: TuyaCloudClient, device_id: str, code: str, dp_id: int, new_value: int
) -> None:
    """Записать ровно один DP и дождаться подтверждения Tuya Cloud."""
    # Получаем новый токен только после истечения действующего.
    if not api.token_validate:
        token_result = await api.async_get_access_token()
        if token_result != "ok":
            raise RuntimeError(f"Ошибка авторизации Tuya: {token_result}")

    # В команду включён только один DP; реле и режимы не затрагиваются.
    body = {"commands": [{"code": code, "value": new_value}]}
    response = await api.async_make_request(
        "POST",
        f"/v1.0/iot-03/devices/{device_id}/commands",
        body=body,
    )
    if not isinstance(response, dict) or not response.get("success"):
        message = (
            response.get("msg", "неизвестная ошибка")
            if isinstance(response, dict) else "нет ответа от Tuya"
        )
        raise RuntimeError(f"Tuya отклонила запись DP {dp_id}: {message}")

    # Команду записи повторно не отправляем: только три чтения с интервалом 2 с.
    for attempt in range(1, 4):
        await asyncio.sleep(2)
        result, status = await api.async_get_device_query_properties(device_id)
        if status != "ok":
            _LOGGER.warning(
                "Tuya Shower: чтение DP %s, попытка %s/3: %s",
                dp_id, attempt, status,
            )
            continue
        actual_value = _read_dp_value(result, code)
        if actual_value == new_value:
            _LOGGER.info("Tuya Shower: DP %s подтверждён: %s °C", dp_id, actual_value)
            return
        _LOGGER.debug(
            "Tuya Shower: DP %s, попытка %s/3: ожидалось %s, получено %s",
            dp_id, attempt, new_value, actual_value,
        )
    raise RuntimeError(
        f"Tuya не подтвердила изменение DP {dp_id} на {new_value} °C"
    )


async def async_setup_platform(
    hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None
) -> None:
    """Создать два независимых регулятора и общий ползунок."""
    device_id = config[CONF_DEVICE_ID]
    # Собственные YAML-реквизиты имеют приоритет; LocalTuya — fallback.
    credentials = get_cloud_credentials(hass, config)
    if credentials is None:
        return

    # Используем собственный клиент Tuya Shower; LocalTuya API не импортируется.
    api = TuyaCloudClient(
        hass=hass,
        region_code=credentials["region"],
        client_id=credentials["client_id"],
        secret=credentials["client_secret"],
        user_id=credentials["user_id"],
    )
    # Общая блокировка не позволяет независимой и групповой записи пересекаться.
    write_lock = asyncio.Lock()
    lower = TuyaShowerNumber(device_id, CONTROLS[0], api, write_lock)
    upper = TuyaShowerNumber(device_id, CONTROLS[1], api, write_lock)
    combined = TuyaShowerCombinedNumber(
        device_id, api, lower, upper, write_lock
    )
    async_add_entities([lower, upper, combined])

    # При старте только читаем значения; команды управления не отправляются.
    await lower.async_refresh_value()
    await upper.async_refresh_value()
    await combined.async_refresh_value()


class TuyaShowerNumber(NumberEntity):
    """Независимый регулятор одного температурного порога S1."""

    _attr_native_min_value = 0
    _attr_native_max_value = 40
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_should_poll = False

    def __init__(self, device_id, control, api, write_lock):
        """Сохранить параметры DP и общий клиент Tuya."""
        self._device_id = device_id
        self._api = api
        self._write_lock = write_lock
        self._code = control["code"]
        self._dp_id = control["dp_id"]
        self._value = None
        self._attr_name = control["name"]
        self._attr_unique_id = f"{device_id}_{control['key']}"

    @property
    def native_value(self):
        """Последнее прочитанное фактическое значение порога."""
        return self._value

    async def async_refresh_value(self):
        """Прочитать фактическое значение DP из Tuya Cloud."""
        try:
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError(f"Ошибка чтения DP: {status}")
            value = _read_dp_value(result, self._code)
            if value is None:
                raise ValueError(f"Tuya не вернула значение {self._code}")
            self._value = value
            self.async_write_ha_state()
        except Exception:
            _LOGGER.exception(
                "Tuya Shower: не удалось прочитать DP %s", self._dp_id
            )


    async def async_set_native_value(self, value: float) -> None:
        """Изменить только свой DP и не допустить пересечения порогов."""
        if not 0 <= value <= 40 or value != int(value):
            raise ValueError("Допустимы целые значения от 0 до 40 °C")
        new_value = int(value)

        async with self._write_lock:
            # Перед отдельной записью проверяем второй порог.
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError("Не удалось прочитать текущие пороги S1")
            other_code = (
                "temp_set_f_3" if self._code == "temp_set" else "temp_set"
            )
            other_value = _read_dp_value(result, other_code)
            if other_value is None:
                raise RuntimeError("Tuya не вернула второй порог S1")
            if self._code == "temp_set" and new_value >= other_value:
                raise ValueError(
                    f"Нижний порог должен быть меньше верхнего ({other_value} °C)"
                )
            if self._code == "temp_set_f_3" and new_value <= other_value:
                raise ValueError(
                    f"Верхний порог должен быть больше нижнего ({other_value} °C)"
                )

            await _async_write_dp_and_confirm(
                self._api, self._device_id, self._code, self._dp_id, new_value
            )
            self._value = new_value
            self.async_write_ha_state()


class TuyaShowerCombinedNumber(NumberEntity):
    """Общий ползунок пары S1; сдвигает оба порога, сохраняя их разницу."""

    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_should_poll = False
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, device_id, api, lower_entity, upper_entity, write_lock):
        """Сохранить ссылки на оба отдельных регулятора."""
        self._device_id = device_id
        self._api = api
        self._lower_entity = lower_entity
        self._upper_entity = upper_entity
        self._write_lock = write_lock
        self._value = None
        self._upper_value = None
        # Ширина диапазона запоминается при чтении и не меняется ползунком.
        self._range_difference = None
        self._attr_name = "ТП душевой — общий порог S1"
        self._attr_unique_id = f"{device_id}_s1_combined"

    @property
    def native_value(self):
        """Значение ползунка соответствует нижнему порогу."""
        return self._value

    @property
    def native_min_value(self):
        """Нижняя граница общего диапазона всегда равна 0 °C."""
        return 0

    @property
    def native_max_value(self):
        """Не позволять верхнему порогу выйти за 40 °C."""
        if self._range_difference is None:
            return 39
        return 40 - self._range_difference

    @property
    def extra_state_attributes(self):
        """Показать оба порога и разницу в атрибутах общей сущности."""
        return {
            "lower_threshold": self._value,
            "upper_threshold": self._upper_value,
            "difference": (
                self._upper_value - self._value
                if self._value is not None and self._upper_value is not None
                else None
            ),
        }

    async def async_refresh_value(self):
        """Прочитать оба DP и сохранить фактическую ширину диапазона."""
        try:
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError(f"Ошибка чтения порогов: {status}")
            lower = _read_dp_value(result, "temp_set")
            upper = _read_dp_value(result, "temp_set_f_3")
            self._lower_entity._value = lower
            self._upper_entity._value = upper
            self._lower_entity.async_write_ha_state()
            self._upper_entity.async_write_ha_state()
            self._upper_value = upper
            # Любая корректная положительная разница допустима.
            # Ползунок сдвигает пару целиком, сохраняя эту разницу.
            difference = (
                upper - lower
                if lower is not None and upper is not None
                else None
            )
            valid_pair = (
                difference is not None
                and difference > 0
                and 0 <= lower < upper <= 40
            )
            self._range_difference = difference if valid_pair else None
            self._value = lower if valid_pair else None
            self.async_write_ha_state()
        except Exception:
            _LOGGER.exception("Tuya Shower: не удалось прочитать пару порогов S1")


    async def async_set_native_value(self, value: float) -> None:
        """Сдвинуть оба порога на одинаковую величину, сохранив их разницу."""
        if value != int(value):
            raise ValueError("Общий порог должен быть целым числом")
        new_lower = int(value)

        async with self._write_lock:
            # Определяем направление по фактическим данным облака Tuya.
            result, status = await self._api.async_get_device_query_properties(
                self._device_id
            )
            if status != "ok":
                raise RuntimeError("Не удалось прочитать текущие пороги S1")
            current_lower = _read_dp_value(result, "temp_set")
            current_upper = _read_dp_value(result, "temp_set_f_3")
            if current_lower is None or current_upper is None:
                raise RuntimeError("Tuya не вернула оба текущих порога S1")

            # Сохраняем ширину существующего диапазона, какой бы она ни была.
            difference = current_upper - current_lower
            if not (0 <= current_lower < current_upper <= 40):
                raise RuntimeError(
                    "Текущая пара порогов некорректна: оба значения должны быть "
                    "в диапазоне 0–40 °C, а верхний порог должен быть выше нижнего."
                )
            max_lower = 40 - difference
            if not 0 <= new_lower <= max_lower:
                raise ValueError(
                    f"При текущей разнице {difference} °C нижний порог "
                    f"можно установить от 0 до {max_lower} °C"
                )
            new_upper = new_lower + difference
            if current_lower == new_lower:
                self._value = current_lower
                self._upper_value = current_upper
                self.async_write_ha_state()
                return

            if new_lower > current_lower:
                # Повышение: сначала верхний порог, затем нижний.
                sequence = (
                    ("temp_set_f_3", 110, new_upper),
                    ("temp_set", 22, new_lower),
                )
            else:
                # Понижение: сначала нижний порог, затем верхний.
                sequence = (
                    ("temp_set", 22, new_lower),
                    ("temp_set_f_3", 110, new_upper),
                )

            try:
                # Следующая команда отправляется только после подтверждения
                # предыдущей командой чтения фактического DP из Tuya Cloud.
                for code, dp_id, target in sequence:
                    await _async_write_dp_and_confirm(
                        self._api, self._device_id, code, dp_id, target
                    )
            except Exception:
                # При ошибке перечитываем оба значения; второй DP не пишем,
                # если подтверждение первого шага не было получено.
                await self.async_refresh_value()
                raise

            # Оба DP подтверждены: обновляем независимые сущности и ползунок.
            self._lower_entity._value = new_lower
            self._upper_entity._value = new_upper
            self._lower_entity.async_write_ha_state()
            self._upper_entity.async_write_ha_state()
            self._value = new_lower
            self._upper_value = new_upper
            self.async_write_ha_state()
