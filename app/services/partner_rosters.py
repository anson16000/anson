from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


def build_partner_riders_payload(
    daily_rows: list[dict[str, Any]],
    tiers: list[dict[str, Any]],
    new_flag: str,
    info: dict[str, Any],
    coalesce_text: Callable[[Any, Any], str],
    to_iso_date: Callable[[Any], str | None],
) -> dict[str, Any]:
    new_rider_daily = defaultdict(int)
    rider_items_map = defaultdict(
        lambda: {
            "rider_id": None,
            "rider_name": None,
            "hire_date": None,
            "total_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "is_new_rider": 0,
        }
    )
    rider_totals = defaultdict(lambda: {"rider_name": None, "completed_orders": 0})
    normalized_new_flag = (new_flag or "all").lower()
    if normalized_new_flag not in {"all", "new", "old"}:
        normalized_new_flag = "all"

    for row in daily_rows:
        total_orders = int(row["total_orders"] or 0)
        completed_orders = int(row["completed_orders"] or 0)
        cancelled_orders = int(row["cancelled_orders"] or 0)
        rider_id_value = row["rider_id"]
        rider_name_value = coalesce_text(row["roster_rider_name"], coalesce_text(row["dwd_rider_name"], rider_id_value))
        is_new_rider = int(row["is_new_rider"] or 0)
        rider_totals[rider_id_value]["rider_name"] = rider_name_value
        rider_totals[rider_id_value]["completed_orders"] += completed_orders
        rider_item = rider_items_map[rider_id_value]
        rider_item["rider_id"] = rider_id_value
        rider_item["rider_name"] = rider_name_value
        rider_item["hire_date"] = to_iso_date(row["hire_date"]) or rider_item["hire_date"]
        rider_item["total_orders"] += total_orders
        rider_item["completed_orders"] += completed_orders
        rider_item["cancelled_orders"] += cancelled_orders
        rider_item["is_new_rider"] = max(int(rider_item["is_new_rider"]), is_new_rider)
        if is_new_rider == 1 and completed_orders > 0:
            date_text = to_iso_date(row["date"])
            if date_text:
                new_rider_daily[date_text] += completed_orders

    rider_items = []
    for item in rider_items_map.values():
        is_new_rider = int(item["is_new_rider"] or 0)
        if normalized_new_flag == "new" and is_new_rider != 1:
            continue
        if normalized_new_flag == "old" and is_new_rider == 1:
            continue
        rider_items.append(item)

    tier_rows = [
        {"label": tier["label"], "min": tier["min"], "max": tier["max"], "rider_count": 0}
        for tier in tiers
    ]
    for rider_total in rider_totals.values():
        completed_orders = int(rider_total["completed_orders"])
        for tier_row in tier_rows:
            max_value = tier_row["max"]
            if completed_orders < tier_row["min"]:
                continue
            if max_value is not None and completed_orders > max_value:
                continue
            tier_row["rider_count"] += 1
            break
    tier_rows.append({"label": "合计", "rider_count": sum(item["rider_count"] for item in tier_rows)})

    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "daily": [
            {"date": bucket_date, "completed_orders": completed_orders}
            for bucket_date, completed_orders in sorted(new_rider_daily.items())
        ],
        "items": sorted(
            rider_items,
            key=lambda item: (-int(item["completed_orders"] or 0), -int(item["total_orders"] or 0), str(item["rider_id"] or "")),
        ),
        "rider_tiers": tier_rows,
    }


def build_partner_merchants_payload(
    merchant_rows: list[dict[str, Any]],
    new_flag: str,
    info: dict[str, Any],
    to_iso_date: Callable[[Any], str | None],
) -> dict[str, Any]:
    new_merchant_daily = defaultdict(int)
    merchant_items_map = defaultdict(
        lambda: {
            "merchant_id": None,
            "merchant_name": None,
            "register_date": None,
            "total_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "is_new_merchant": 0,
        }
    )
    normalized_new_flag = (new_flag or "all").lower()
    if normalized_new_flag not in {"all", "new", "old"}:
        normalized_new_flag = "all"

    for row in merchant_rows:
        total_orders = int(row["total_orders"] or 0)
        completed_orders = int(row["completed_orders"] or 0)
        cancelled_orders = int(row["cancelled_orders"] or 0)
        merchant_id_value = row["merchant_id"]
        merchant_name_value = row.get("shop_name") or row["merchant_name"] or merchant_id_value
        is_new_merchant = int(row["is_new_merchant"] or 0)
        merchant_item = merchant_items_map[merchant_id_value]
        merchant_item["merchant_id"] = merchant_id_value
        merchant_item["merchant_name"] = merchant_name_value
        merchant_item["register_date"] = to_iso_date(row["register_date"]) or merchant_item["register_date"]
        merchant_item["total_orders"] += total_orders
        merchant_item["completed_orders"] += completed_orders
        merchant_item["cancelled_orders"] += cancelled_orders
        merchant_item["is_new_merchant"] = max(int(merchant_item["is_new_merchant"]), is_new_merchant)
        if is_new_merchant == 1 and completed_orders > 0:
            date_text = to_iso_date(row["date"])
            if date_text:
                new_merchant_daily[date_text] += completed_orders

    merchant_items = []
    for item in merchant_items_map.values():
        is_new_merchant = int(item["is_new_merchant"] or 0)
        if normalized_new_flag == "new" and is_new_merchant != 1:
            continue
        if normalized_new_flag == "old" and is_new_merchant == 1:
            continue
        merchant_items.append(item)

    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "daily": [
            {"date": bucket_date, "completed_orders": completed_orders}
            for bucket_date, completed_orders in sorted(new_merchant_daily.items())
        ],
        "items": sorted(
            merchant_items,
            key=lambda item: (-int(item["completed_orders"] or 0), -int(item["total_orders"] or 0), str(item["merchant_id"] or "")),
        ),
    }
