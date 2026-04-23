from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable


def build_partner_riders_payload(
    daily_rows: list[dict[str, Any]],
    tiers: list[dict[str, Any]],
    new_flag: str,
    info: dict[str, Any],
    coalesce_text: Callable[[Any, Any], str],
    to_iso_date: Callable[[Any], str | None],
    start_date: date | None = None,
    end_date: date | None = None,
    target_daily_completed_orders: int = 10,
    target_completed_days: int = 10,
) -> dict[str, Any]:
    new_rider_daily = defaultdict(int)
    date_set = set()
    rider_items_map = defaultdict(
        lambda: {
            "rider_id": None,
            "rider_name": None,
            "hire_date": None,
            "completed_orders": 0,
            "qualified_days": 0,
            "is_new_rider": 0,
            "daily_completed_orders": {},
        }
    )
    rider_totals = defaultdict(lambda: {"rider_name": None, "completed_orders": 0})
    normalized_new_flag = (new_flag or "all").lower()
    if normalized_new_flag not in {"all", "new", "old"}:
        normalized_new_flag = "all"

    for row in daily_rows:
        completed_orders = int(row["completed_orders"] or 0)
        rider_id_value = row["rider_id"]
        date_text = to_iso_date(row["date"])
        rider_name_value = coalesce_text(row["roster_rider_name"], coalesce_text(row["dwd_rider_name"], rider_id_value))
        is_new_rider = int(row["is_new_rider"] or 0)
        rider_totals[rider_id_value]["rider_name"] = rider_name_value
        rider_totals[rider_id_value]["completed_orders"] += completed_orders
        rider_item = rider_items_map[rider_id_value]
        rider_item["rider_id"] = rider_id_value
        rider_item["rider_name"] = rider_name_value
        rider_item["hire_date"] = to_iso_date(row["hire_date"]) or rider_item["hire_date"]
        rider_item["completed_orders"] += completed_orders
        rider_item["is_new_rider"] = max(int(rider_item["is_new_rider"]), is_new_rider)
        if date_text:
            date_set.add(date_text)
            rider_item["daily_completed_orders"][date_text] = completed_orders
        if is_new_rider == 1 and completed_orders > 0:
            if date_text:
                new_rider_daily[date_text] += completed_orders

    if start_date and end_date and start_date <= end_date:
        total_days = (end_date - start_date).days + 1
        date_columns = [(start_date + timedelta(days=offset)).isoformat() for offset in range(total_days)]
    else:
        date_columns = sorted(date_set)
    daily_target = max(int(target_daily_completed_orders or 0), 1)
    days_target = max(int(target_completed_days or 0), 1)
    rider_items = []
    for item in rider_items_map.values():
        is_new_rider = int(item["is_new_rider"] or 0)
        if normalized_new_flag == "new" and is_new_rider != 1:
            continue
        if normalized_new_flag == "old" and is_new_rider == 1:
            continue
        item["daily_completed_orders"] = {
            date_text: int(item["daily_completed_orders"].get(date_text, 0) or 0)
            for date_text in date_columns
        }
        item["completed_orders"] = sum(item["daily_completed_orders"].values())
        item["qualified_days"] = sum(
            1 for completed_orders in item["daily_completed_orders"].values() if int(completed_orders or 0) >= daily_target
        )
        item["is_target_met"] = 1 if int(item["qualified_days"] or 0) >= days_target else 0
        rider_items.append(item)

    total_daily_completed_orders = {
        date_text: sum(int(item["daily_completed_orders"].get(date_text, 0) or 0) for item in rider_items)
        for date_text in date_columns
    }
    total_row = {
        "__pinnedTop": True,
        "__is_total": True,
        "rider_id": "-",
        "rider_name": "-",
        "hire_date": "-",
        "completed_orders": sum(int(item["completed_orders"] or 0) for item in rider_items),
        "qualified_days": sum(int(item["qualified_days"] or 0) for item in rider_items),
        "is_new_rider": None,
        "is_target_met": sum(int(item["is_target_met"] or 0) for item in rider_items),
        "daily_completed_orders": total_daily_completed_orders,
    }

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
        "date_columns": date_columns,
        "daily": [
            {"date": bucket_date, "completed_orders": completed_orders}
            for bucket_date, completed_orders in sorted(new_rider_daily.items())
        ],
        "items": sorted(
            [total_row, *rider_items],
            key=lambda item: (
                1 if item.get("__pinnedTop") else 0,
                -sum(int(value or 0) for value in (item.get("daily_completed_orders") or {}).values()),
                str(item["rider_id"] or ""),
            ),
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
