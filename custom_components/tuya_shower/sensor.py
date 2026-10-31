"""Read-only sensors for the Tuya shower controller.

Tuya Cloud communication and credential handling belong to this integration.
LocalTuya credentials remain supported only as a backward-compatible fallback.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_DEVICE_ID, PERCENTAGE, UnitOfTemperature
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
from .tuya_api import TuyaCloudClient

_LOGGER = logging.getLogger(__name__)

# Запрашиваем состояние контроллера раз в 30 секунд.
SCAN_INTERVAL = timedelta(seconds=30)

# ID устройства передаётся из configuration.yaml.
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_CLIENT_ID): cv.string,
        vol.Optional(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_USER_ID): cv.string,
        vol.Optional(CONF_REGION): cv.string,
    }
)

# Описание датчиков: ключ, имя, код DP, единица, класс, делитель.
# Температура DP temp_current приходит в десятых долях градуса.
SENSORS = (
    (
        "temperature",
        "Температура в душевой",
        "temp_current",
        UnitOfTemperature.CELSIUS,
        "temperature",
        10,
    ),
    (
        "humidity",
        "Влажность в душевой",
        "humidity_value",
        PERCENTAGE,
        "humidity",
        1,
    ),
    (
        "s1_lower",
        "ТП душевой — нижний порог S1",
        "temp_set",
        UnitOfTemperature.CELSIUS,
        "temperature",
        1,
    ),
    (
        "s1_upper",
        "ТП душевой — верхний порог S1",
        "temp_set_f_3",
        UnitOfTemperature.CELSIUS,
        "temperature",
        1,
    ),
)


def _properties_to_dict(result: Any) -> dict[str, Any]:
    """Преобразовать ответ Tuya в словарь значений по коду DP."""
    properties = result.get("properties", []) if isinstance(result, dict) else []

    # Некоторые варианты ответа Tuya уже содержат словарь code -> value.
    if isinstance(properties, dict):
        return properties

    # Стандартный ответ shadow/properties содержит список объектов DP.
    values: dict[str, Any] = {}
    for item in properties:
        if isinstance(item, dict) and item.get("code"):
            values[item["code"]] = item.get("value")

    if not values:
        raise ValueError("Tuya вернула пустой список свойств устройства")

    return values


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Создать датчики и запустить периодическое чтение Tuya Cloud."""
    device_id = config[CONF_DEVICE_ID]

    # Сначала используем собственные YAML-реквизиты Tuya Shower.
    # LocalTuya остаётся только совместимым источником для старой конфигурации.
    credentials = get_cloud_credentials(hass, config)
    if credentials is None:
        return

    # Создаём собственный клиент на HTTP-сессии, управляемой Home Assistant.
    api = TuyaCloudClient(
        hass=hass,
        region_code=credentials["region"],
        client_id=credentials["client_id"],
        secret=credentials["client_secret"],
        user_id=credentials["user_id"],
    )

    # Создаём сущности заранее: при временной сетевой ошибке они останутся
    # в Home Assistant и смогут получить значения при следующем опросе.
    entities = [
        TuyaShowerSensor(
            device_id,
            key,
            name,
            code,
            unit,
            device_class,
            divisor,
        )
        for key, name, code, unit, device_class, divisor in SENSORS
    ]
    async_add_entities(entities)

    async def async_update(_now=None) -> None:
        """Только читать свойства устройства; команды управления не отправлять."""
        try:
            # Клиент сам получает токен при необходимости и обновляет его
            # при ответе Tuya об истёкшей или недействительной авторизации.
            result, status = await api.async_get_device_query_properties(device_id)
            if status != "ok":
                raise RuntimeError(f"Ошибка чтения свойств Tuya: {status}")

            values = _properties_to_dict(result)

            # Обновляем все четыре сущности значениями из одного ответа API.
            for entity in entities:
                entity.set_value(values.get(entity.dp_code))

        except Exception:
            # Ошибка отдельного опроса не удаляет сущности и не останавливает
            # последующие обновления по расписанию.
            _LOGGER.exception("Tuya Shower: не удалось обновить датчики")

    # Первый запрос выполняем сразу, следующие — каждые 30 секунд.
    await async_update()
    async_track_time_interval(hass, async_update, SCAN_INTERVAL)


class TuyaShowerSensor(SensorEntity):
    """Один датчик контроллера с последним полученным значением."""

    _attr_should_poll = False

    def __init__(
        self,
        device_id: str,
        key: str,
        name: str,
        code: str,
        unit: str,
        device_class: str,
        divisor: int,
    ) -> None:
        """Сохранить описание DP и метаданные сущности Home Assistant."""
        self.dp_code = code
        self._divisor = divisor
        self._raw_value = None

        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    def set_value(self, raw_value: Any) -> None:
        """Сохранить новое значение DP и обновить состояние сущности."""
        self._raw_value = raw_value
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Вернуть значение с учётом масштаба, заданного для DP."""
        if self._raw_value is None:
            return None

        try:
            return float(self._raw_value) / self._divisor
        except (TypeError, ValueError):
            return None
