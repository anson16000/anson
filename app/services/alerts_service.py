from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_partner_fluctuation_payload(
    rows: list[Any],
    settings_alerts,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.partner_id].append(row)

    large_daily = overrides.get("large_city_daily_threshold") or settings_alerts.large_city_daily_threshold
    large_abs = overrides.get("large_city_change_abs") or settings_alerts.large_city_change_abs
    large_pct = (
        overrides["large_city_change_pct"]
        if overrides.get("large_city_change_pct") is not None
        else settings_alerts.large_city_change_pct
    )
    medium_daily = overrides.get("medium_city_daily_threshold") or settings_alerts.medium_city_daily_threshold
    medium_abs = overrides.get("medium_city_change_abs") or settings_alerts.medium_city_change_abs
    medium_pct = (
        overrides["medium_city_change_pct"]
        if overrides.get("medium_city_change_pct") is not None
        else settings_alerts.medium_city_change_pct
    )
    small_abs = overrides.get("small_city_change_abs") or settings_alerts.small_city_change_abs
    small_pct = (
        overrides["small_city_change_pct"]
        if overrides.get("small_city_change_pct") is not None
        else settings_alerts.small_city_change_pct
    )

    alerts = []
    for partner_id_value, series in grouped.items():
        if len(series) < 2:
            continue
        latest = series[-1]
        previous = series[:-1]
        baseline = sum(item.completed_orders for item in previous[-7:]) / min(len(previous), 7)
        change_abs = latest.completed_orders - baseline
        change_pct = change_abs / baseline if baseline else 0.0

        if baseline >= large_daily:
            hit = abs(change_abs) >= large_abs and abs(change_pct) >= large_pct
            city_level = "large"
        elif baseline >= medium_daily:
            hit = abs(change_abs) >= medium_abs and abs(change_pct) >= medium_pct
            city_level = "medium"
        else:
            hit = abs(change_abs) >= small_abs and abs(change_pct) >= small_pct
            city_level = "small"
        if not hit:
            continue

        alerts.append(
            {
                "partner_id": partner_id_value,
                "partner_name": latest.partner_name,
                "date": latest.date.isoformat(),
                "latest_completed_orders": latest.completed_orders,
                "baseline_completed_orders": round(baseline, 2),
                "change_abs": round(change_abs, 2),
                "change_pct": round(change_pct, 4),
                "new_riders": latest.new_riders,
                "new_merchants": latest.new_merchants,
                "active_riders": latest.active_riders,
                "active_merchants": latest.active_merchants,
                "cancel_rate": latest.cancel_rate,
                "hq_subsidy_total": latest.hq_subsidy_total,
                "partner_subsidy_total": latest.partner_subsidy_total,
                "city_level": city_level,
            }
        )

    alerts.sort(key=lambda item: abs(item["change_pct"]), reverse=True)
    return {
        "alerts": alerts[:50],
        "applied_thresholds": {
            "large_city_daily_threshold": large_daily,
            "large_city_change_abs": large_abs,
            "large_city_change_pct": large_pct,
            "medium_city_daily_threshold": medium_daily,
            "medium_city_change_abs": medium_abs,
            "medium_city_change_pct": medium_pct,
            "small_city_change_abs": small_abs,
            "small_city_change_pct": small_pct,
        },
    }
