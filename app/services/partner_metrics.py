from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


def build_partner_overview_payload(
    *,
    info: dict[str, Any],
    partner_id: str,
    latest_row: Any,
    rows: list[Any],
    dwd_rows: list[Any],
    summary: dict[str, float],
    active_riders: int,
    active_merchants: int,
    new_riders: int,
    new_merchants: int,
    amount_row: dict[str, Any],
    threshold: int,
    sla_minutes: int,
    active_completed_threshold: int,
    day_count: int,
    calc_duration_minutes: Callable[[Any, Any], float | None],
    safe_ratio: Callable[[float, float], float],
    calc_efficiency: Callable[[float, float], float],
    build_order_summary: Callable[..., dict[str, Any]],
    build_health_score: Callable[[dict[str, Any], int], dict[str, Any]],
) -> dict[str, Any]:
    actual_received_total = float(amount_row["completed_amount_paid"] or 0.0)
    rider_commission_total = float(amount_row["rider_income_total"] or 0.0)
    partner_income_total = float(amount_row["partner_income_total"] or 0.0)
    partner_subsidy_total = float(amount_row["partner_subsidy_total"] or 0.0)
    partner_profit = partner_income_total - partner_subsidy_total
    valid_cancel_orders = int(amount_row["valid_cancel_orders"] or 0)

    runtime_total_orders = 0
    runtime_completed_orders = 0
    runtime_cancelled_orders = 0
    runtime_valid_orders = 0
    runtime_new_rider_orders = 0
    runtime_new_merchant_orders = 0
    on_time_orders = 0
    sla_on_time_orders = 0
    sla_overtime_orders = 0
    sla_completed_base = 0

    for row in dwd_rows:
        runtime_total_orders += 1
        if row.is_cancelled:
            runtime_cancelled_orders += 1

        is_valid_cancel = bool(row.is_cancelled and row.is_paid and (row.pay_cancel_minutes or 0) > threshold)

        if row.is_completed:
            runtime_completed_orders += 1
            if row.is_new_rider_order:
                runtime_new_rider_orders += 1
            if row.is_new_merchant_order:
                runtime_new_merchant_orders += 1

            duration_minutes = calc_duration_minutes(row.accept_time, row.complete_time)
            if duration_minutes is not None:
                sla_completed_base += 1
                if duration_minutes <= 30:
                    on_time_orders += 1
                if duration_minutes <= sla_minutes:
                    sla_on_time_orders += 1
                else:
                    sla_overtime_orders += 1

        if row.is_completed or is_valid_cancel:
            runtime_valid_orders += 1

    total_orders = runtime_total_orders if dwd_rows else summary["total_orders"]
    valid_orders = runtime_valid_orders if dwd_rows else summary["valid_orders"]
    completed_orders = runtime_completed_orders if dwd_rows else summary["completed_orders"]
    cancelled_orders = runtime_cancelled_orders if dwd_rows else summary["cancelled_orders"]
    new_rider_orders = runtime_new_rider_orders if dwd_rows else summary["new_rider_orders"]
    new_merchant_orders = runtime_new_merchant_orders if dwd_rows else summary["new_merchant_orders"]

    health_score = build_health_score(
        {
            "total_orders": total_orders,
            "valid_orders": valid_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "valid_cancel_orders": valid_cancel_orders,
            "active_riders": active_riders,
            "active_merchants": active_merchants,
            "new_merchant_orders": new_merchant_orders,
            "actual_received_total": actual_received_total,
            "partner_profit": partner_profit,
        },
        day_count=day_count,
    )

    cancel_rate = safe_ratio(cancelled_orders, total_orders)
    diagnostics: list[str] = []
    if cancel_rate > 0.20:
        diagnostics.append("Cancel rate is high. Review capacity response and timeout acceptance.")
    if new_rider_orders and new_rider_orders < completed_orders * 0.1:
        diagnostics.append("New rider contribution is low. Review onboarding activation and coaching.")
    if new_merchant_orders and new_merchant_orders < completed_orders * 0.1:
        diagnostics.append("New merchant contribution is low. Review first-order conversion and merchant follow-up.")
    if not diagnostics:
        diagnostics.append("Current city operation is stable.")

    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "partner_id": partner_id,
        "partner_name": latest_row.partner_name,
        "province": latest_row.province,
        "city": latest_row.city,
        "district": latest_row.district,
        "summary": {
            **build_order_summary(
                total_orders,
                valid_orders,
                completed_orders,
                cancelled_orders,
                active_merchants=active_merchants,
                new_merchants=new_merchants,
                active_riders=active_riders,
                new_riders=new_riders,
                efficiency=calc_efficiency(completed_orders, active_riders),
                actual_received_total=round(actual_received_total, 2),
                rider_commission_total=round(rider_commission_total, 2),
                partner_income_total=round(partner_income_total, 2),
                partner_subsidy_total=round(partner_subsidy_total, 2),
                partner_profit=round(partner_profit, 2),
                avg_ticket_price=round(actual_received_total / completed_orders, 2) if completed_orders else 0.0,
                rider_avg_commission=round(rider_commission_total / completed_orders, 2) if completed_orders else 0.0,
                rider_avg_income=round(rider_commission_total / completed_orders, 2) if completed_orders else 0.0,
                partner_avg_profit=round(partner_profit / completed_orders, 2) if completed_orders else 0.0,
                on_time_orders=int(on_time_orders),
                on_time_rate=safe_ratio(on_time_orders, sla_completed_base),
                sla_minutes=sla_minutes,
                sla_on_time_orders=int(sla_on_time_orders),
                sla_overtime_orders=int(sla_overtime_orders),
                sla_on_time_rate=safe_ratio(sla_on_time_orders, sla_completed_base),
                sla_overtime_rate=safe_ratio(sla_overtime_orders, sla_completed_base),
                health_score=health_score,
                hq_subsidy_total=round(summary["hq_subsidy_total"], 2),
            ),
        },
        "applied_thresholds": {
            "active_completed_threshold": active_completed_threshold,
            "valid_cancel_threshold_minutes": threshold,
            "sla_minutes": sla_minutes,
        },
        "diagnostics": diagnostics,
    }


def build_partner_health_payload(
    *,
    info: dict[str, Any],
    partner_id: str,
    row: dict[str, Any],
    active_riders: int,
    active_merchants: int,
    day_count: int,
    threshold: int,
    active_completed_threshold: int,
    build_health_score: Callable[[dict[str, Any], int], dict[str, Any]],
) -> dict[str, Any]:
    partner_profit = float(row.get("partner_income_total") or 0.0) - float(row.get("partner_subsidy_total") or 0.0)
    health_score = build_health_score(
        {
            "total_orders": float(row.get("total_orders") or 0.0),
            "valid_orders": float(row.get("valid_orders") or 0.0),
            "completed_orders": float(row.get("completed_orders") or 0.0),
            "cancelled_orders": float(row.get("cancelled_orders") or 0.0),
            "valid_cancel_orders": float(row.get("valid_cancel_orders") or 0.0),
            "active_riders": active_riders,
            "active_merchants": active_merchants,
            "new_merchant_orders": float(row.get("new_merchant_orders") or 0.0),
            "actual_received_total": float(row.get("actual_received_total") or 0.0),
            "partner_profit": partner_profit,
        },
        day_count=day_count,
    )
    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "partner_id": partner_id,
        "health_score": health_score,
        "applied_thresholds": {
            "active_completed_threshold": active_completed_threshold,
            "valid_cancel_threshold_minutes": threshold,
        },
    }


def build_partner_daily_payload(
    *,
    info: dict[str, Any],
    dwd_rows: list[Any],
    threshold: int,
    sla_minutes: int,
    calc_duration_minutes: Callable[[Any, Any], float | None],
    safe_ratio: Callable[[float, float], float],
) -> dict[str, Any]:
    grouped = defaultdict(
        lambda: {
            "total_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "valid_orders": 0,
            "actual_received_total": 0.0,
            "rider_commission_total": 0.0,
            "partner_income_total": 0.0,
            "partner_subsidy_total": 0.0,
            "new_rider_orders": 0,
            "new_merchant_orders": 0,
            "on_time_orders": 0,
            "sla_on_time_orders": 0,
            "sla_overtime_orders": 0,
            "sla_completed_base": 0,
        }
    )
    for row in dwd_rows:
        if not row.order_date:
            continue
        bucket = grouped[row.order_date.isoformat()]
        bucket["total_orders"] += 1
        if row.is_completed:
            bucket["completed_orders"] += 1
            bucket["actual_received_total"] += float(row.amount_paid or 0.0)
            bucket["rider_commission_total"] += float(row.rider_income or 0.0)
            bucket["partner_income_total"] += float(row.partner_income or 0.0)
            bucket["partner_subsidy_total"] += float(row.partner_subsidy_amount or 0.0)
            if row.is_new_rider_order:
                bucket["new_rider_orders"] += 1
            if row.is_new_merchant_order:
                bucket["new_merchant_orders"] += 1
            duration_minutes = calc_duration_minutes(row.accept_time, row.complete_time)
            if duration_minutes is not None:
                bucket["sla_completed_base"] += 1
                if duration_minutes <= 30:
                    bucket["on_time_orders"] += 1
                if duration_minutes <= sla_minutes:
                    bucket["sla_on_time_orders"] += 1
                else:
                    bucket["sla_overtime_orders"] += 1
        if row.is_cancelled:
            bucket["cancelled_orders"] += 1
        is_valid_cancel = bool(row.is_cancelled and row.is_paid and (row.pay_cancel_minutes or 0) > threshold)
        if row.is_completed or is_valid_cancel:
            bucket["valid_orders"] += 1

    return {
        "data_version": info.get("data_version"),
        "latest_ready_month": info.get("latest_ready_month"),
        "items": [
            {
                "date": bucket_date,
                "total_orders": int(bucket["total_orders"]),
                "valid_orders": int(bucket["valid_orders"]),
                "valid_completed_orders": int(bucket["completed_orders"]),
                "valid_completion_rate": safe_ratio(bucket["completed_orders"], bucket["valid_orders"]),
                "completed_orders": int(bucket["completed_orders"]),
                "cancelled_orders": int(bucket["cancelled_orders"]),
                "completion_rate": safe_ratio(bucket["completed_orders"], bucket["total_orders"]),
                "cancel_rate": safe_ratio(bucket["cancelled_orders"], bucket["total_orders"]),
                "new_rider_orders": int(bucket["new_rider_orders"]),
                "new_merchant_orders": int(bucket["new_merchant_orders"]),
                "actual_received_total": round(float(bucket["actual_received_total"]), 2),
                "rider_commission_total": round(float(bucket["rider_commission_total"]), 2),
                "partner_income_total": round(float(bucket["partner_income_total"]), 2),
                "partner_subsidy_total": round(float(bucket["partner_subsidy_total"]), 2),
                "partner_profit": round(float(bucket["partner_income_total"]) - float(bucket["partner_subsidy_total"]), 2),
                "on_time_orders": int(bucket["on_time_orders"]),
                "on_time_rate": safe_ratio(bucket["on_time_orders"], bucket["sla_completed_base"]),
                "sla_minutes": sla_minutes,
                "sla_on_time_orders": int(bucket["sla_on_time_orders"]),
                "sla_overtime_orders": int(bucket["sla_overtime_orders"]),
                "sla_on_time_rate": safe_ratio(bucket["sla_on_time_orders"], bucket["sla_completed_base"]),
                "sla_overtime_rate": safe_ratio(bucket["sla_overtime_orders"], bucket["sla_completed_base"]),
                "rider_avg_commission": round(float(bucket["rider_commission_total"]) / float(bucket["completed_orders"]), 2) if bucket["completed_orders"] else 0.0,
            }
            for bucket_date, bucket in sorted(grouped.items())
        ],
        "applied_thresholds": {
            "valid_cancel_threshold_minutes": threshold,
            "sla_minutes": sla_minutes,
        },
    }
