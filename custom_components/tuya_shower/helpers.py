"""Общие функции разбора ответов Tuya Cloud."""
from __future__ import annotations

from typing import Any


def properties_to_dict(result: Any) -> dict[str, Any]:
    """Преобразовать ответ Tuya в словарь значений по коду DP."""
    properties = result.get("properties", []) if isinstance(result, dict) else []
    if isinstance(properties, dict):
        if not properties:
            raise ValueError("Tuya вернула пустой словарь свойств устройства")
        return properties
    values: dict[str, Any] = {}
    if isinstance(properties, list):
        for item in properties:
            if isinstance(item, dict) and item.get("code"):
                values[item["code"]] = item.get("value")
    if not values:
        raise ValueError("Tuya вернула пустой или некорректный список свойств устройства")
    return values
