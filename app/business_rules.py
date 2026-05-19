from __future__ import annotations

from collections.abc import Iterable
from typing import Any


DEFAULT_EXCLUDED_PARTNER_IDS: tuple[str, ...] = ("101",)


def normalize_partner_ids(values: Iterable[Any] | None) -> tuple[str, ...]:
    if not values:
        return DEFAULT_EXCLUDED_PARTNER_IDS
    normalized = tuple(str(value).strip() for value in values if str(value).strip())
    return normalized or DEFAULT_EXCLUDED_PARTNER_IDS


def excluded_partner_ids_from_settings(settings: Any | None = None) -> tuple[str, ...]:
    if settings is None:
        return DEFAULT_EXCLUDED_PARTNER_IDS
    business = getattr(settings, "business", None)
    values = getattr(business, "excluded_partner_ids", None)
    return normalize_partner_ids(values)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_literal_list(values: Iterable[Any] | None) -> str:
    return ", ".join(sql_literal(value) for value in normalize_partner_ids(values))
