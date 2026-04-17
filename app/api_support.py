from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import case, func


def api_response(data: Any, message: str = "success", code: int = 200) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().astimezone().isoformat(),
    }


def safe_ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator, 4)


def filter_by_date(rows: list[Any], start_date: date | None, end_date: date | None, attr: str = "date") -> list[Any]:
    filtered = []
    for row in rows:
        value = getattr(row, attr)
        if start_date and value < start_date:
            continue
        if end_date and value > end_date:
            continue
        filtered.append(row)
    return filtered


def resolve_compare_periods(
    start_date: date | None,
    end_date: date | None,
    baseline_start: date | None,
    baseline_end: date | None,
    compare_start: date | None,
    compare_end: date | None,
) -> tuple[tuple[date | None, date | None], tuple[date | None, date | None]]:
    if compare_start or compare_end:
        current_start = compare_start or start_date
        current_end = compare_end or end_date
    else:
        current_start = start_date
        current_end = end_date

    if baseline_start or baseline_end:
        return (baseline_start, baseline_end), (current_start, current_end)

    if current_start and current_end:
        span = max((current_end - current_start).days, 0)
        derived_end = current_start - timedelta(days=1)
        derived_start = derived_end - timedelta(days=span)
        return (derived_start, derived_end), (current_start, current_end)

    return (baseline_start, baseline_end), (current_start, current_end)


def period_contains(value: date, window: tuple[date | None, date | None]) -> bool:
    start_date, end_date = window
    if start_date and value < start_date:
        return False
    if end_date and value > end_date:
        return False
    return True


def day_count(start_date: date | None, end_date: date | None, fallback_dates: list[date] | None = None) -> int:
    if start_date and end_date:
        return max((end_date - start_date).days + 1, 1)
    if fallback_dates:
        return max(len({value for value in fallback_dates if value}), 1)
    return 1


def validate_query_window(start_date: date | None, end_date: date | None, max_days: int = 31) -> None:
    if not start_date or not end_date:
        return
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期。")
    total_days = (end_date - start_date).days + 1
    if total_days > max_days:
        raise HTTPException(status_code=400, detail=f"单次查询最多支持 {max_days} 天，请缩小日期范围。")


def parse_partner_tiers(raw_value: str | None) -> list[dict[str, Any]]:
    default_tiers = [
        {"label": "0-9单/日", "min": 0, "max": 9},
        {"label": "10-49单/日", "min": 10, "max": 49},
        {"label": "50-99单/日", "min": 50, "max": 99},
        {"label": "100单+/日", "min": 100, "max": None},
    ]
    if not raw_value:
        return default_tiers
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return default_tiers
    if not isinstance(parsed, list):
        return default_tiers

    tiers: list[dict[str, Any]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        try:
            min_value = int(item.get("min", 0) or 0)
            max_raw = item.get("max")
            max_value = None if max_raw in (None, "", "null") else int(max_raw)
        except (TypeError, ValueError):
            continue
        if max_value is not None and max_value < min_value:
            continue
        tiers.append(
            {
                "label": str(item.get("label") or f"层级{index + 1}"),
                "min": min_value,
                "max": max_value,
            }
        )
    return tiers or default_tiers


def parse_generic_tiers(raw_value: str | None, default_tiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw_value:
        return default_tiers
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return default_tiers
    if not isinstance(parsed, list):
        return default_tiers

    tiers: list[dict[str, Any]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        try:
            min_value = int(item.get("min", 0) or 0)
            max_raw = item.get("max")
            max_value = None if max_raw in (None, "", "null") else int(max_raw)
        except (TypeError, ValueError):
            continue
        if max_value is not None and max_value < min_value:
            continue
        tiers.append(
            {
                "label": str(item.get("label") or f"层级{index + 1}"),
                "min": min_value,
                "max": max_value,
            }
        )
    return tiers or default_tiers


def default_rider_tiers() -> list[dict[str, Any]]:
    return [
        {"label": "1-9单", "min": 1, "max": 9},
        {"label": "10-29单", "min": 10, "max": 29},
        {"label": "30-49单", "min": 30, "max": 49},
        {"label": "50单+", "min": 50, "max": None},
    ]


def coalesce_text(value: str | None, fallback: str) -> str:
    text = (value or "").strip()
    return text or fallback


def to_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def sum_bool(expr):
    return func.sum(case((expr, 1), else_=0))


def calc_efficiency(completed_orders: float, rider_count: float) -> float:
    return safe_ratio(completed_orders, rider_count)
