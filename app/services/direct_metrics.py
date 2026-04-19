from __future__ import annotations

from typing import Any, Callable


def build_direct_new_riders_payload(
    *,
    rows: list[dict[str, Any]],
    info: dict[str, Any],
    coalesce_text: Callable[[Any, Any], str],
    to_iso_date: Callable[[Any], str | None],
) -> dict[str, Any]:
    items = [
        {
            "partner_id": row["partner_id"],
            "partner_name": row["partner_name"],
            "rider_id": row["rider_id"],
            "rider_name": coalesce_text(row["roster_rider_name"], coalesce_text(row["dwd_rider_name"], row["rider_id"])),
            "hire_date": to_iso_date(row["hire_date"]),
            "total_orders": int(row["total_orders"] or 0),
            "completed_orders": int(row["completed_orders"] or 0),
        }
        for row in rows
    ]
    items.sort(key=lambda item: item["completed_orders"], reverse=True)
    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "items": items[:100],
    }


def build_direct_new_merchants_payload(
    *,
    rows: list[dict[str, Any]],
    info: dict[str, Any],
    to_iso_date: Callable[[Any], str | None],
    safe_ratio: Callable[[float, float], float],
) -> dict[str, Any]:
    items = [
        {
            "partner_id": row["partner_id"],
            "partner_name": row["partner_name"],
            "merchant_id": row["merchant_id"],
            "merchant_name": row["merchant_name"] or row["merchant_id"],
            "register_date": to_iso_date(row["register_date"]),
            "total_orders": int(row["total_orders"] or 0),
            "completed_orders": int(row["completed_orders"] or 0),
            "completion_rate": safe_ratio(row["completed_orders"] or 0, row["total_orders"] or 0),
        }
        for row in rows
    ]
    items.sort(key=lambda item: item["completed_orders"], reverse=True)
    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "items": items[:100],
    }
