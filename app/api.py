from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, func, select

from app.api_support import (
    api_response,
    calc_efficiency as _calc_efficiency,
    coalesce_text as _coalesce_text,
    day_count as _day_count,
    default_rider_tiers as _default_rider_tiers,
    filter_by_date as _filter_by_date,
    parse_generic_tiers as _parse_generic_tiers,
    parse_partner_tiers as _parse_partner_tiers,
    period_contains as _period_contains,
    resolve_compare_periods as _resolve_compare_periods,
    safe_ratio,
    sum_bool as _sum_bool,
    to_iso_date as _to_iso_date,
    validate_query_window as _validate_query_window,
)
from app.config import load_settings, resolve_path
from app.database import session_scope
from app.logging_config import setup_logging
from app.models import (
    AdsAdminPartnerMetrics,
    AdsDirectCancelDayMetrics,
    AdsDirectCouponMetrics,
    AdsDirectHourMetrics,
    AdsDirectMerchantDayMetrics,
    AdsDirectNewMerchantMetrics,
    AdsDirectNewRiderMetrics,
    AdsDirectOrderSourceDayMetrics,
    AdsPartnerDayMetrics,
    AdsPartnerHourMetrics,
    AdsPartnerMerchantDayMetrics,
    AdsPartnerRiderDayMetrics,
    EtlJobRun,
    EtlStageMetrics,
    FileRegistry,
    DwdOrderDetail,
    MerchantRoster,
    PartnerRoster,
    PartnerSlaConfig,
    RiderRoster,
)
from app.pipeline import get_latest_import_info, import_all, init_database
from app.services.alerts_service import build_partner_fluctuation_payload
from app.services.direct_metrics import build_direct_new_merchants_payload, build_direct_new_riders_payload
from app.services.partner_entities import build_merchant_like_users
from app.services.partner_metrics import (
    build_partner_daily_payload,
    build_partner_health_payload,
    build_partner_overview_payload,
)
from app.services.partner_rosters import build_partner_merchants_payload, build_partner_riders_payload


def _calc_duration_minutes(start_value: datetime | None, end_value: datetime | None) -> float | None:
    if not start_value or not end_value:
        return None
    return (end_value - start_value).total_seconds() / 60


def _get_partner_sla_minutes(session, partner_id: str | None, default_minutes: int = 30) -> int:
    if not partner_id:
        return int(default_minutes)
    config = session.get(PartnerSlaConfig, partner_id)
    if not config or not config.sla_minutes:
        return int(default_minutes)
    return int(config.sla_minutes)


def _build_sla_metrics_from_rows(rows: list[Any], sla_minutes: int) -> dict[str, float]:
    metrics = {
        "on_time_orders": 0,
        "on_time_rate": 0.0,
        "sla_on_time_orders": 0,
        "sla_overtime_orders": 0,
        "sla_on_time_rate": 0.0,
        "sla_overtime_rate": 0.0,
        "sla_completed_base": 0,
    }
    for row in rows:
        if not row.is_completed:
            continue
        duration_minutes = _calc_duration_minutes(row.accept_time, row.complete_time)
        if duration_minutes is None:
            continue
        metrics["sla_completed_base"] += 1
        if duration_minutes <= 30:
            metrics["on_time_orders"] += 1
        if duration_minutes <= sla_minutes:
            metrics["sla_on_time_orders"] += 1
        else:
            metrics["sla_overtime_orders"] += 1

    base = metrics["sla_completed_base"]
    metrics["on_time_rate"] = safe_ratio(metrics["on_time_orders"], base)
    metrics["sla_on_time_rate"] = safe_ratio(metrics["sla_on_time_orders"], base)
    metrics["sla_overtime_rate"] = safe_ratio(metrics["sla_overtime_orders"], base)
    return metrics


def _build_hourly_metrics(
    rows: list[Any],
    threshold: int,
    include_date: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    per_bucket = defaultdict(
        lambda: {
            "total_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "valid_orders": 0,
            "accepted_riders": set(),
        }
    )

    def order_bucket_key(row: Any):
        if row.order_date is None or row.order_hour is None:
            return None
        if include_date:
            return (row.order_date.isoformat(), int(row.order_hour))
        return int(row.order_hour)

    def accept_bucket_key(row: Any):
        if row.accept_hour is None or not row.rider_id:
            return None
        accept_date = None
        if row.accept_time:
            if isinstance(row.accept_time, datetime):
                accept_date = row.accept_time.date()
            elif isinstance(row.accept_time, date):
                accept_date = row.accept_time
        accept_date_text = _to_iso_date(accept_date or row.order_date)
        if include_date:
            if not accept_date_text:
                return None
            return (accept_date_text, int(row.accept_hour))
        return int(row.accept_hour)

    for row in rows:
        bucket_key = order_bucket_key(row)
        if bucket_key is not None:
            bucket = per_bucket[bucket_key]
            bucket["total_orders"] += 1
            if row.is_completed:
                bucket["completed_orders"] += 1
            if row.is_cancelled:
                bucket["cancelled_orders"] += 1
            is_valid_cancel = bool(row.is_cancelled and row.is_paid and (row.pay_cancel_minutes or 0) > threshold)
            if row.is_completed or is_valid_cancel:
                bucket["valid_orders"] += 1

        accepted_key = accept_bucket_key(row)
        if accepted_key is not None:
            per_bucket[accepted_key]["accepted_riders"].add(row.rider_id)

    items: list[dict[str, Any]] = []
    by_hour = defaultdict(lambda: {"total_orders": 0, "completed_orders": 0, "cancelled_orders": 0, "valid_orders": 0, "accepted_rider_count": 0})

    def sort_key(key: Any):
        if include_date:
            return key[0], key[1]
        return key

    for bucket_key in sorted(per_bucket.keys(), key=sort_key):
        bucket = per_bucket[bucket_key]
        accepted_rider_count = len(bucket["accepted_riders"])
        total_orders = int(bucket["total_orders"])
        completed_orders = int(bucket["completed_orders"])
        cancelled_orders = int(bucket["cancelled_orders"])
        valid_orders = int(bucket["valid_orders"])
        if include_date:
            date_text, hour = bucket_key
        else:
            date_text, hour = None, bucket_key

        item = {
            "hour": int(hour),
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "valid_orders": valid_orders,
            "valid_completed_orders": completed_orders,
            "valid_completion_rate": safe_ratio(completed_orders, valid_orders),
            "completion_rate": safe_ratio(completed_orders, total_orders),
            "cancel_rate": safe_ratio(cancelled_orders, total_orders),
            "accepted_rider_count": accepted_rider_count,
            "efficiency": _calc_efficiency(completed_orders, accepted_rider_count),
        }
        if include_date:
            item["date"] = date_text
        items.append(item)

        summary_bucket = by_hour[int(hour)]
        summary_bucket["total_orders"] += total_orders
        summary_bucket["completed_orders"] += completed_orders
        summary_bucket["cancelled_orders"] += cancelled_orders
        summary_bucket["valid_orders"] += valid_orders
        summary_bucket["accepted_rider_count"] += accepted_rider_count

    hourly_summary = [
        {
            "hour": hour,
            "total_orders": int(values["total_orders"]),
            "completed_orders": int(values["completed_orders"]),
            "cancelled_orders": int(values["cancelled_orders"]),
            "valid_orders": int(values["valid_orders"]),
            "valid_completed_orders": int(values["completed_orders"]),
            "valid_completion_rate": safe_ratio(values["completed_orders"], values["valid_orders"]),
            "completion_rate": safe_ratio(values["completed_orders"], values["total_orders"]),
            "cancel_rate": safe_ratio(values["cancelled_orders"], values["total_orders"]),
            "accepted_rider_count": int(values["accepted_rider_count"]),
            "efficiency": _calc_efficiency(values["completed_orders"], values["accepted_rider_count"]),
        }
        for hour, values in sorted(by_hour.items())
    ]

    return items, hourly_summary


def _apply_dwd_filters(
    stmt,
    start_date: date | None = None,
    end_date: date | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    partner_id: str | None = None,
):
    if start_date:
        stmt = stmt.where(DwdOrderDetail.order_date >= start_date)
    if end_date:
        stmt = stmt.where(DwdOrderDetail.order_date <= end_date)
    if province:
        stmt = stmt.where(DwdOrderDetail.province == province)
    if city:
        stmt = stmt.where(DwdOrderDetail.city == city)
    if district:
        stmt = stmt.where(DwdOrderDetail.district == district)
    if partner_id:
        stmt = stmt.where(DwdOrderDetail.partner_id == partner_id)
    return stmt


def _apply_partner_day_filters(
    stmt,
    start_date: date | None = None,
    end_date: date | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    partner_id: str | None = None,
):
    if start_date:
        stmt = stmt.where(AdsPartnerDayMetrics.date >= start_date)
    if end_date:
        stmt = stmt.where(AdsPartnerDayMetrics.date <= end_date)
    if province:
        stmt = stmt.where(AdsPartnerDayMetrics.province == province)
    if city:
        stmt = stmt.where(AdsPartnerDayMetrics.city == city)
    if district:
        stmt = stmt.where(AdsPartnerDayMetrics.district == district)
    if partner_id:
        stmt = stmt.where(AdsPartnerDayMetrics.partner_id == partner_id)
    return stmt


def _count_active_entities(
    session,
    entity_column,
    threshold: int,
    start_date: date | None = None,
    end_date: date | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    partner_id: str | None = None,
) -> int:
    completed_orders = func.sum(case((DwdOrderDetail.is_completed.is_(True), 1), else_=0))
    stmt = select(entity_column).where(entity_column.is_not(None))
    stmt = _apply_dwd_filters(stmt, start_date, end_date, province, city, district, partner_id)
    stmt = stmt.group_by(entity_column).having(completed_orders >= max(int(threshold or 1), 1))
    return len(session.execute(stmt).all())


def _count_new_entities(
    session,
    entity_column,
    new_flag_column,
    start_date: date | None = None,
    end_date: date | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    partner_id: str | None = None,
) -> int:
    completed_orders = func.sum(case((DwdOrderDetail.is_completed.is_(True), 1), else_=0))
    stmt = (
        select(entity_column)
        .where(entity_column.is_not(None))
        .where(new_flag_column.is_(True))
    )
    stmt = _apply_dwd_filters(stmt, start_date, end_date, province, city, district, partner_id)
    stmt = stmt.group_by(entity_column).having(completed_orders > 0)
    return len(session.execute(stmt).all())


def _score_high(value: float, warning: float, target: float, max_points: float) -> float:
    current = float(value or 0.0)
    if current <= warning:
        return 0.0
    if current >= target:
        return round(max_points, 2)
    return round((current - warning) / max(target - warning, 1e-9) * max_points, 2)


def _score_low(value: float, target: float, warning: float, max_points: float) -> float:
    current = float(value or 0.0)
    if current <= target:
        return round(max_points, 2)
    if current >= warning:
        return 0.0
    return round((warning - current) / max(warning - target, 1e-9) * max_points, 2)


def _health_band(score: float) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def _health_label(score: float) -> str:
    if score >= 80:
        return "健康"
    if score >= 60:
        return "关注"
    return "风险"


def _build_health_score(metrics: dict[str, Any], day_count: int) -> dict[str, Any]:
    total_orders = float(metrics.get("total_orders") or 0.0)
    valid_orders = float(metrics.get("valid_orders") or 0.0)
    completed_orders = float(metrics.get("completed_orders") or 0.0)
    cancelled_orders = float(metrics.get("cancelled_orders") or 0.0)
    valid_cancel_orders = float(metrics.get("valid_cancel_orders") or max(valid_orders - completed_orders, 0.0))
    active_riders = float(metrics.get("active_riders") or 0.0)
    active_merchants = float(metrics.get("active_merchants") or 0.0)
    new_merchant_orders = float(metrics.get("new_merchant_orders") or 0.0)
    actual_received_total = float(metrics.get("actual_received_total") or 0.0)
    partner_profit = float(metrics.get("partner_profit") or 0.0)

    completion_rate = safe_ratio(completed_orders, total_orders)
    cancel_rate = safe_ratio(cancelled_orders, total_orders)
    valid_cancel_rate = safe_ratio(valid_cancel_orders, valid_orders)
    avg_daily_orders = total_orders / max(day_count, 1)
    efficiency = safe_ratio(completed_orders, active_riders)
    avg_ticket_price = safe_ratio(actual_received_total, completed_orders)
    partner_avg_profit = safe_ratio(partner_profit, completed_orders)
    new_merchant_share = safe_ratio(new_merchant_orders, completed_orders)

    dimension_scores = {
        "scale_growth": round(_score_high(avg_daily_orders, 10, 100, 20), 2),
        "fulfillment_quality": round(
            _score_high(completion_rate, 0.60, 0.90, 10)
            + _score_low(cancel_rate, 0.08, 0.30, 10)
            + _score_low(valid_cancel_rate, 0.03, 0.15, 5),
            2,
        ),
        "capacity_health": round(
            _score_high(efficiency, 0.8, 3.5, 12)
            + _score_high(active_riders, 3, 30, 8),
            2,
        ),
        "merchant_operation": round(
            _score_high(active_merchants, 5, 50, 10)
            + _score_high(new_merchant_share, 0.02, 0.10, 5),
            2,
        ),
        "revenue_quality": round(
            _score_high(avg_ticket_price, 3, 12, 8)
            + _score_high(partner_avg_profit, 0.2, 2.0, 12),
            2,
        ),
    }
    total_score = round(sum(dimension_scores.values()), 1)

    issues: list[str] = []
    if cancel_rate >= 0.20:
        issues.append("取消率偏高")
    if valid_cancel_rate >= 0.08:
        issues.append("有效取消偏高")
    if efficiency < 1.2:
        issues.append("人效偏低")
    if partner_profit < 0:
        issues.append("合伙人利润为负")
    if not issues:
        issues.append("经营整体稳定")

    return {
        "total_score": total_score,
        "label": _health_label(total_score),
        "band": _health_band(total_score),
        "dimension_scores": dimension_scores,
        "issues": issues[:3],
    }


def _summarize_health_scores(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "average_score": 0.0,
            "green_count": 0,
            "yellow_count": 0,
            "red_count": 0,
        }
    average_score = round(sum(float(item["total_score"]) for item in items) / len(items), 1)
    return {
        "average_score": average_score,
        "green_count": sum(1 for item in items if item["band"] == "green"),
        "yellow_count": sum(1 for item in items if item["band"] == "yellow"),
        "red_count": sum(1 for item in items if item["band"] == "red"),
    }


def _completed_financial_totals(
    session,
    start_date: date | None = None,
    end_date: date | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    partner_id: str | None = None,
) -> dict[str, float]:
    stmt = select(
        func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("actual_received_total"),
        func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_income), else_=0.0)).label("rider_commission_total"),
        func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
        func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
    )
    stmt = _apply_dwd_filters(stmt, start_date, end_date, province, city, district, partner_id)
    row = session.execute(stmt).mappings().first() or {}
    actual_received_total = float(row.get("actual_received_total") or 0.0)
    rider_commission_total = float(row.get("rider_commission_total") or 0.0)
    partner_income_total = float(row.get("partner_income_total") or 0.0)
    partner_subsidy_total = float(row.get("partner_subsidy_total") or 0.0)
    partner_profit = partner_income_total - partner_subsidy_total
    return {
        "actual_received_total": round(actual_received_total, 2),
        "rider_commission_total": round(rider_commission_total, 2),
        "partner_income_total": round(partner_income_total, 2),
        "partner_subsidy_total": round(partner_subsidy_total, 2),
        "partner_profit": round(partner_profit, 2),
    }


def _merge_partner_directory(partner_rows: list[Any], ads_partner_rows: list[Any]) -> list[dict[str, Any]]:
    roster_map: dict[str, dict[str, Any]] = {
        row.partner_id: {
            "partner_id": row.partner_id,
            "partner_name": row.partner_name,
            "province": row.province,
            "city": row.city,
            "district": row.district,
        }
        for row in partner_rows
        if row.partner_id
    }
    ads_map: dict[str, dict[str, Any]] = {}
    for row in ads_partner_rows:
        if not row.partner_id:
            continue
        ads_map[row.partner_id] = {
            "partner_id": row.partner_id,
            "partner_name": row.partner_name or row.partner_id,
            "province": row.province,
            "city": row.city,
            "district": row.district,
        }

    partners_map: dict[str, dict[str, Any]] = {}
    for current_partner_id in set(roster_map) | set(ads_map):
        merged: dict[str, Any] = {
            "partner_id": current_partner_id,
            "partner_name": None,
            "province": None,
            "city": None,
            "district": None,
        }
        if current_partner_id in ads_map:
            merged.update({k: v for k, v in ads_map[current_partner_id].items() if v is not None})
        if current_partner_id in roster_map:
            merged.update({k: v for k, v in roster_map[current_partner_id].items() if v is not None})
        partners_map[current_partner_id] = merged

    return sorted(partners_map.values(), key=lambda item: (item.get("partner_name") or "", item.get("partner_id") or ""))


def _build_order_summary(total_orders: float, valid_orders: float, completed_orders: float, cancelled_orders: float, **extra_fields: Any) -> dict[str, Any]:
    return {
        "total_orders": int(total_orders),
        "valid_orders": int(valid_orders),
        "valid_completed_orders": int(completed_orders),
        "valid_completion_rate": safe_ratio(completed_orders, valid_orders),
        "completed_orders": int(completed_orders),
        "cancelled_orders": int(cancelled_orders),
        "completion_rate": safe_ratio(completed_orders, total_orders),
        "cancel_rate": safe_ratio(cancelled_orders, total_orders),
        **extra_fields,
    }


def create_app() -> FastAPI:
    settings = load_settings()
    setup_logging(str(resolve_path(settings.paths.logs)))
    _, session_factory = init_database(settings)

    app = FastAPI(title="Delivery Dashboard", version="1.0.0")
    static_dir = resolve_path(settings.paths.static)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(static_dir / "admin.html")

    @app.get("/partner", include_in_schema=False)
    def partner_page():
        return FileResponse(static_dir / "partner.html")

    @app.get("/partner/hourly", include_in_schema=False)
    def partner_hourly_page():
        return FileResponse(static_dir / "hourly.html")

    @app.get("/partner/entities", include_in_schema=False)
    def partner_entities_page():
        return FileResponse(static_dir / "entities.html")

    @app.get("/alerts", include_in_schema=False)
    def alerts_page():
        return FileResponse(static_dir / "alerts.html")

    @app.get("/direct", include_in_schema=False)
    def direct_page():
        return RedirectResponse(url="/partner?section=direct", status_code=307)

    @app.get("/api/v1/meta")
    def meta():
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            partner_rows = list(session.scalars(select(PartnerRoster).order_by(PartnerRoster.partner_name)))
            ads_partner_rows = list(
                session.scalars(
                    select(AdsAdminPartnerMetrics).order_by(
                        AdsAdminPartnerMetrics.partner_name,
                        AdsAdminPartnerMetrics.partner_id,
                    )
                )
            )

        partners = _merge_partner_directory(partner_rows, ads_partner_rows)
        return api_response(
            {
                "system": info,
                "partners": partners,
                "regions": {
                    "provinces": sorted({item.get("province") for item in partners if item.get("province")}),
                    "cities": sorted({item.get("city") for item in partners if item.get("city")}),
                    "districts": sorted({item.get("district") for item in partners if item.get("district")}),
                },
            }
        )

    @app.post("/api/v1/import")
    def trigger_import():
        result = import_all(settings)
        return api_response(result.__dict__)

    @app.get("/api/v1/import/status")
    def import_status():
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            latest_job = session.scalar(select(EtlJobRun).order_by(EtlJobRun.started_at.desc()))
            stages = []
            if latest_job:
                stages = [
                    {
                        "stage_name": row.stage_name,
                        "duration_seconds": row.duration_seconds,
                        "input_rows": row.input_rows,
                        "output_rows": row.output_rows,
                        "status": row.status,
                        "detail": row.detail,
                    }
                    for row in session.scalars(
                        select(EtlStageMetrics).where(EtlStageMetrics.run_id == latest_job.run_id).order_by(EtlStageMetrics.started_at)
                    )
                ]
            files = [
                {
                    "file_name": row.file_name,
                    "file_type": row.file_type,
                    "order_month": row.order_month,
                    "stage_status": row.stage_status,
                    "imported_at": row.imported_at.isoformat(),
                    "status": row.status,
                    "error_message": row.error_message,
                }
                for row in session.scalars(select(FileRegistry).order_by(FileRegistry.imported_at.desc()).limit(50))
            ]
        return api_response(
            {
                "summary": info,
                "latest_job": {
                    "run_id": latest_job.run_id if latest_job else None,
                    "status": latest_job.status if latest_job else None,
                    "started_at": latest_job.started_at.isoformat() if latest_job else None,
                    "ended_at": latest_job.ended_at.isoformat() if latest_job and latest_job.ended_at else None,
                    "affected_months": latest_job.affected_months if latest_job else None,
                    "total_seconds": latest_job.total_seconds if latest_job else None,
                },
                "stages": stages,
                "files": files,
            }
        )

    @app.get("/api/v1/admin/metrics")
    def admin_metrics(
        start_date: date | None = Query(default=None),
        end_date: date | None = Query(default=None),
        province: str | None = Query(default=None),
        city: str | None = Query(default=None),
        district: str | None = Query(default=None),
        partner_id: str | None = Query(default=None),
        only_new_partner: bool = Query(default=False),
        only_new_merchant: bool = Query(default=False),
        only_new_rider: bool = Query(default=False),
        active_completed_threshold: int = Query(default=1, ge=1),
        ranking_level: str = Query(default="all"),
        partner_tiers: str | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(AdsAdminPartnerMetrics)
            if start_date:
                stmt = stmt.where(AdsAdminPartnerMetrics.date >= start_date)
            if end_date:
                stmt = stmt.where(AdsAdminPartnerMetrics.date <= end_date)
            if province:
                stmt = stmt.where(AdsAdminPartnerMetrics.province == province)
            if city:
                stmt = stmt.where(AdsAdminPartnerMetrics.city == city)
            if district:
                stmt = stmt.where(AdsAdminPartnerMetrics.district == district)
            if partner_id:
                stmt = stmt.where(AdsAdminPartnerMetrics.partner_id == partner_id)
            rows = list(session.scalars(stmt))

            filtered: list[AdsAdminPartnerMetrics] = []
            for row in rows:
                if only_new_partner and not row.is_new_partner:
                    continue
                if only_new_merchant and row.new_merchants == 0:
                    continue
                if only_new_rider and row.new_riders == 0:
                    continue
                filtered.append(row)

            active_partners = _count_active_entities(
                session,
                DwdOrderDetail.partner_id,
                active_completed_threshold,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )
            active_riders = _count_active_entities(
                session,
                DwdOrderDetail.rider_id,
                active_completed_threshold,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )
            active_merchants = _count_active_entities(
                session,
                DwdOrderDetail.merchant_id,
                active_completed_threshold,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )
            new_partners = _count_new_entities(
                session,
                DwdOrderDetail.partner_id,
                DwdOrderDetail.is_new_partner_order,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )
            new_riders = _count_new_entities(
                session,
                DwdOrderDetail.rider_id,
                DwdOrderDetail.is_new_rider_order,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )
            new_merchants = _count_new_entities(
                session,
                DwdOrderDetail.merchant_id,
                DwdOrderDetail.is_new_merchant_order,
                start_date,
                end_date,
                province,
                city,
                district,
                partner_id,
            )

            partner_stats_stmt = select(
                DwdOrderDetail.partner_id,
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                func.max(DwdOrderDetail.province).label("province"),
                func.max(DwdOrderDetail.city).label("city"),
                func.max(DwdOrderDetail.district).label("district"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_valid_order.is_(True)).label("valid_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("completed_amount_paid"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_income), else_=0.0)).label("rider_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_id), else_=None))).label("active_rider_count"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.merchant_id), else_=None))).label("active_merchant_count"),
                func.sum(case(((DwdOrderDetail.is_completed.is_(True)) & (DwdOrderDetail.is_new_rider_order.is_(True)), 1), else_=0)).label("new_rider_orders"),
                func.sum(case(((DwdOrderDetail.is_completed.is_(True)) & (DwdOrderDetail.is_new_merchant_order.is_(True)), 1), else_=0)).label("new_merchant_orders"),
            ).where(DwdOrderDetail.partner_id.is_not(None))
            partner_stats_stmt = _apply_dwd_filters(partner_stats_stmt, start_date, end_date, province, city, district, partner_id)
            partner_stats_stmt = partner_stats_stmt.group_by(DwdOrderDetail.partner_id)
            partner_stats = list(session.execute(partner_stats_stmt).mappings())

            partner_window_stmt = select(
                DwdOrderDetail.partner_id.label("partner_id"),
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                func.max(PartnerRoster.open_date).label("open_date"),
                func.sum(
                    case(
                        (
                            DwdOrderDetail.is_completed.is_(True),
                            case(
                                (
                                    func.datediff("day", PartnerRoster.open_date, DwdOrderDetail.order_date) <= 30,
                                    1,
                                ),
                                else_=0,
                            ),
                        ),
                        else_=0,
                    )
                ).label("completed_30"),
                func.sum(
                    case(
                        (
                            DwdOrderDetail.is_completed.is_(True),
                            case(
                                (
                                    (func.datediff("day", PartnerRoster.open_date, DwdOrderDetail.order_date) > 30)
                                    & (func.datediff("day", PartnerRoster.open_date, DwdOrderDetail.order_date) <= 60),
                                    1,
                                ),
                                else_=0,
                            ),
                        ),
                        else_=0,
                    )
                ).label("completed_60"),
                func.sum(
                    case(
                        (
                            DwdOrderDetail.is_completed.is_(True),
                            case(
                                (
                                    (func.datediff("day", PartnerRoster.open_date, DwdOrderDetail.order_date) > 60)
                                    & (func.datediff("day", PartnerRoster.open_date, DwdOrderDetail.order_date) <= 90),
                                    1,
                                ),
                                else_=0,
                            ),
                        ),
                        else_=0,
                    )
                ).label("completed_90"),
            ).select_from(DwdOrderDetail).join(PartnerRoster, PartnerRoster.partner_id == DwdOrderDetail.partner_id, isouter=True)
            partner_window_stmt = _apply_dwd_filters(partner_window_stmt, start_date, end_date, province, city, district, partner_id)
            partner_window_stmt = partner_window_stmt.where(PartnerRoster.open_date.is_not(None)).group_by(DwdOrderDetail.partner_id)
            partner_window_rows = list(session.execute(partner_window_stmt).mappings())

        summary = defaultdict(float)
        date_buckets = defaultdict(lambda: {"total_orders": 0, "valid_orders": 0, "completed_orders": 0, "cancelled_orders": 0})
        partner_buckets = defaultdict(
            lambda: {
                "partner_name": "",
                "province": None,
                "city": None,
                "district": None,
                "total_orders": 0,
                "valid_orders": 0,
                "completed_orders": 0,
                "cancelled_orders": 0,
                "is_new_partner": False,
            }
        )

        for row in filtered:
            summary["total_orders"] += row.total_orders
            summary["valid_orders"] += row.valid_orders
            summary["completed_orders"] += row.completed_orders
            summary["cancelled_orders"] += row.cancelled_orders
            summary["hq_subsidy_total"] += row.hq_subsidy_total
            summary["partner_subsidy_total"] += row.partner_subsidy_total

            date_bucket = date_buckets[row.date.isoformat()]
            date_bucket["total_orders"] += row.total_orders
            date_bucket["valid_orders"] += row.valid_orders
            date_bucket["completed_orders"] += row.completed_orders
            date_bucket["cancelled_orders"] += row.cancelled_orders

            bucket = partner_buckets[row.partner_id]
            bucket["partner_name"] = row.partner_name or row.partner_id
            bucket["province"] = row.province or bucket["province"]
            bucket["city"] = row.city or bucket["city"]
            bucket["district"] = row.district or bucket["district"]
            bucket["total_orders"] += row.total_orders
            bucket["valid_orders"] += row.valid_orders
            bucket["completed_orders"] += row.completed_orders
            bucket["cancelled_orders"] += row.cancelled_orders
            bucket["is_new_partner"] = bucket["is_new_partner"] or bool(row.is_new_partner)

        ranking_level = (ranking_level or "all").lower()
        region_ranking_rows: list[dict[str, Any]] = []
        if ranking_level == "all":
            for bucket in partner_stats:
                completed_orders = int(bucket["completed_orders"] or 0)
                total_orders = int(bucket["total_orders"] or 0)
                valid_orders = int(bucket["valid_orders"] or 0)
                cancelled_orders = int(bucket["cancelled_orders"] or 0)
                active_rider_count = int(bucket["active_rider_count"] or 0)
                active_merchant_count = int(bucket["active_merchant_count"] or 0)
                completed_amount_paid = float(bucket["completed_amount_paid"] or 0.0)
                partner_income_total = float(bucket["partner_income_total"] or 0.0)
                partner_subsidy_total = float(bucket["partner_subsidy_total"] or 0.0)
                region_ranking_rows.append(
                    {
                        "region": bucket["partner_name"] or bucket["partner_id"] or "未分配区域",
                        "total_orders": total_orders,
                        "valid_orders": valid_orders,
                        "valid_completed_orders": completed_orders,
                        "valid_completion_rate": safe_ratio(completed_orders, valid_orders),
                        "completed_orders": completed_orders,
                        "cancelled_orders": cancelled_orders,
                        "completion_rate": safe_ratio(completed_orders, total_orders),
                        "cancel_rate": safe_ratio(cancelled_orders, total_orders),
                        "active_riders": active_rider_count,
                        "active_merchants": active_merchant_count,
                        "efficiency": _calc_efficiency(completed_orders, active_rider_count),
                        "avg_ticket_price": round(completed_amount_paid / completed_orders, 2) if completed_orders else 0.0,
                        "partner_profit": round(partner_income_total - partner_subsidy_total, 2),
                    }
                )
        else:
            region_stmt = select(
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                func.max(DwdOrderDetail.province).label("province"),
                func.max(DwdOrderDetail.city).label("city"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_valid_order.is_(True)).label("valid_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("completed_amount_paid"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_id), else_=None))).label("active_rider_count"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.merchant_id), else_=None))).label("active_merchant_count"),
            )
            region_stmt = _apply_dwd_filters(region_stmt, start_date, end_date, province, city, district, partner_id)
            if ranking_level == "province":
                region_stmt = region_stmt.group_by(DwdOrderDetail.province)
            else:
                region_stmt = region_stmt.group_by(DwdOrderDetail.province, DwdOrderDetail.city)
            with session_scope(session_factory) as session:
                region_rows = list(session.execute(region_stmt).mappings())
            for row in region_rows:
                completed_orders = int(row["completed_orders"] or 0)
                total_orders = int(row["total_orders"] or 0)
                valid_orders = int(row["valid_orders"] or 0)
                cancelled_orders = int(row["cancelled_orders"] or 0)
                active_rider_count = int(row["active_rider_count"] or 0)
                active_merchant_count = int(row["active_merchant_count"] or 0)
                completed_amount_paid = float(row["completed_amount_paid"] or 0.0)
                partner_income_total = float(row["partner_income_total"] or 0.0)
                partner_subsidy_total = float(row["partner_subsidy_total"] or 0.0)
                if ranking_level == "province":
                    region_label = row["province"] or row["partner_name"] or "未分配区域"
                else:
                    region_label = " / ".join([part for part in (row["province"], row["city"]) if part]) or row["partner_name"] or "未分配区域"
                region_ranking_rows.append(
                    {
                        "region": region_label,
                        "total_orders": total_orders,
                        "valid_orders": valid_orders,
                        "valid_completed_orders": completed_orders,
                        "valid_completion_rate": safe_ratio(completed_orders, valid_orders),
                        "completed_orders": completed_orders,
                        "cancelled_orders": cancelled_orders,
                        "completion_rate": safe_ratio(completed_orders, total_orders),
                        "cancel_rate": safe_ratio(cancelled_orders, total_orders),
                        "active_riders": active_rider_count,
                        "active_merchants": active_merchant_count,
                        "efficiency": _calc_efficiency(completed_orders, active_rider_count),
                        "avg_ticket_price": round(completed_amount_paid / completed_orders, 2) if completed_orders else 0.0,
                        "partner_profit": round(partner_income_total - partner_subsidy_total, 2),
                    }
                )

        day_count = _day_count(start_date, end_date, [item.date for item in filtered if item.date])
        tiers = _parse_partner_tiers(partner_tiers)
        tier_rows = [
            {
                "label": tier["label"],
                "min": tier["min"],
                "max": tier["max"],
                "partner_count": 0,
                "completed_orders": 0,
                "total_orders": 0,
                "completed_amount_paid": 0.0,
                "partner_income_total": 0.0,
                "active_rider_count": 0,
            }
            for tier in tiers
        ]
        partner_total = 0
        for bucket in partner_stats:
            completed_orders = int(bucket["completed_orders"] or 0)
            if completed_orders <= 0:
                continue
            partner_total += 1
            total_orders = int(bucket["total_orders"] or 0)
            avg_daily_orders = total_orders / day_count if day_count else 0.0
            for tier_row in tier_rows:
                max_value = tier_row["max"]
                if avg_daily_orders < tier_row["min"]:
                    continue
                if max_value is not None and avg_daily_orders > max_value:
                    continue
                tier_row["partner_count"] += 1
                tier_row["total_orders"] += total_orders
                tier_row["completed_orders"] += completed_orders
                tier_row["completed_amount_paid"] += float(bucket["completed_amount_paid"] or 0.0)
                tier_row["partner_income_total"] += float(bucket["partner_income_total"] or 0.0)
                tier_row["active_rider_count"] += int(bucket["active_rider_count"] or 0)
                break

        partner_tier_stats = []
        totals_row = {
            "label": "合计",
            "partner_count": 0,
            "completed_orders": 0,
            "avg_daily_orders": 0.0,
            "avg_ticket_price": 0.0,
            "efficiency": 0.0,
            "avg_income_per_order": 0.0,
        }
        for tier_row in tier_rows:
            partner_count = int(tier_row["partner_count"])
            completed_orders = int(tier_row["completed_orders"])
            total_orders = int(tier_row["total_orders"])
            completed_amount_paid = float(tier_row["completed_amount_paid"])
            partner_income_total = float(tier_row["partner_income_total"])
            active_rider_count = int(tier_row["active_rider_count"])
            item = {
                "label": tier_row["label"],
                "partner_count": partner_count,
                "completed_orders": completed_orders,
                "avg_daily_orders": round(total_orders / (partner_count * day_count), 2) if partner_count and day_count else 0.0,
                "avg_ticket_price": round(completed_amount_paid / completed_orders, 2) if completed_orders else 0.0,
                "efficiency": _calc_efficiency(completed_orders, active_rider_count),
                "avg_income_per_order": round(partner_income_total / completed_orders, 2) if completed_orders else 0.0,
            }
            totals_row["partner_count"] += partner_count
            totals_row["completed_orders"] += completed_orders
            partner_tier_stats.append(item)

        if totals_row["partner_count"]:
            tier_total_orders = sum(int(row["total_orders"] or 0) for row in partner_stats if int(row["completed_orders"] or 0) > 0)
            tier_total_paid = sum(float(row["completed_amount_paid"] or 0.0) for row in partner_stats if int(row["completed_orders"] or 0) > 0)
            tier_total_income = sum(float(row["partner_income_total"] or 0.0) for row in partner_stats if int(row["completed_orders"] or 0) > 0)
            tier_total_riders = sum(int(row["active_rider_count"] or 0) for row in partner_stats if int(row["completed_orders"] or 0) > 0)
            totals_row["avg_daily_orders"] = round(tier_total_orders / (totals_row["partner_count"] * day_count), 2) if day_count else 0.0
            totals_row["avg_ticket_price"] = round(tier_total_paid / totals_row["completed_orders"], 2) if totals_row["completed_orders"] else 0.0
            totals_row["efficiency"] = _calc_efficiency(totals_row["completed_orders"], tier_total_riders)
            totals_row["avg_income_per_order"] = round(tier_total_income / totals_row["completed_orders"], 2) if totals_row["completed_orders"] else 0.0
            partner_tier_stats.append(totals_row)

        new_partner_performance = []
        for row in partner_window_rows:
            for window_key, window_label in (
                ("completed_30", "30日表现"),
                ("completed_60", "60日表现"),
                ("completed_90", "90日表现"),
            ):
                completed_orders = int(row[window_key] or 0)
                if completed_orders <= 0:
                    continue
                new_partner_performance.append(
                    {
                        "partner_id": row["partner_id"],
                        "partner_name": row["partner_name"] or row["partner_id"],
                        "window_label": window_label,
                        "completed_orders": completed_orders,
                        "open_date": row["open_date"].isoformat() if row["open_date"] else None,
                    }
                )
        new_partner_performance.sort(key=lambda item: (item["window_label"], -item["completed_orders"]))

        with session_scope(session_factory) as session:
            completed_financials = _completed_financial_totals(
                session,
                start_date=start_date,
                end_date=end_date,
                province=province,
                city=city,
                district=district,
                partner_id=partner_id,
            )
        partner_metrics_by_id: dict[str, dict[str, Any]] = {}
        health_items = []
        for bucket in partner_stats:
            total_orders = float(bucket["total_orders"] or 0.0)
            valid_orders = float(bucket["valid_orders"] or 0.0)
            completed_orders = float(bucket["completed_orders"] or 0.0)
            cancelled_orders = float(bucket["cancelled_orders"] or 0.0)
            valid_cancel_orders = max(valid_orders - completed_orders, 0.0)
            active_riders_count = int(bucket["active_rider_count"] or 0)
            active_merchants_count = int(bucket["active_merchant_count"] or 0)
            completed_amount_paid = float(bucket["completed_amount_paid"] or 0.0)
            partner_profit = float(bucket["partner_income_total"] or 0.0) - float(bucket["partner_subsidy_total"] or 0.0)
            partner_metrics = {
                "partner_id": bucket["partner_id"],
                "partner_name": bucket["partner_name"] or bucket["partner_id"],
                "region": bucket["partner_name"] or bucket["partner_id"] or "未分配区域",
                **_build_order_summary(
                    total_orders,
                    valid_orders,
                    completed_orders,
                    cancelled_orders,
                    active_riders=active_riders_count,
                    active_merchants=active_merchants_count,
                    efficiency=_calc_efficiency(completed_orders, active_riders_count),
                    avg_ticket_price=round(completed_amount_paid / completed_orders, 2) if completed_orders else 0.0,
                    partner_profit=round(partner_profit, 2),
                ),
            }
            partner_metrics_by_id[str(bucket["partner_id"])] = partner_metrics
            health_items.append(
                {
                    "partner_id": bucket["partner_id"],
                    "partner_name": bucket["partner_name"] or bucket["partner_id"],
                    **partner_metrics,
                    **_build_health_score(
                        {
                            "total_orders": total_orders,
                            "valid_orders": valid_orders,
                            "completed_orders": completed_orders,
                            "cancelled_orders": cancelled_orders,
                            "valid_cancel_orders": valid_cancel_orders,
                            "active_riders": float(bucket["active_rider_count"] or 0.0),
                            "active_merchants": float(bucket["active_merchant_count"] or 0.0),
                            "new_merchant_orders": float(bucket["new_merchant_orders"] or 0.0),
                            "actual_received_total": completed_amount_paid,
                            "partner_profit": partner_profit,
                        },
                        day_count=day_count,
                    ),
                }
            )
        health_score_summary = _summarize_health_scores(health_items)
        focus_partner_items = sorted(
            [item for item in health_items if item.get("band") == "yellow"],
            key=lambda item: (item.get("total_score", 0), -(item.get("completed_orders", 0) or 0)),
        )[:50]
        risk_partner_items = sorted(
            [item for item in health_items if item.get("band") == "red"],
            key=lambda item: (item.get("total_score", 0), -(item.get("completed_orders", 0) or 0)),
        )[:50]

        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "summary": {
                    **_build_order_summary(
                        summary["total_orders"],
                        summary["valid_orders"],
                        summary["completed_orders"],
                        summary["cancelled_orders"],
                        active_partners=active_partners,
                        active_merchants=active_merchants,
                        active_riders=active_riders,
                        new_partners=new_partners,
                        new_merchants=new_merchants,
                        new_riders=new_riders,
                        partner_total=partner_total,
                        hq_subsidy_total=round(summary["hq_subsidy_total"], 2),
                        partner_subsidy_total=round(summary["partner_subsidy_total"], 2),
                        actual_received_total=completed_financials["actual_received_total"],
                        rider_commission_total=completed_financials["rider_commission_total"],
                        partner_income_total=completed_financials["partner_income_total"],
                        partner_profit_total=completed_financials["partner_profit"],
                        health_score_summary=health_score_summary,
                    ),
                },
                "daily_trend": sorted(
                    [
                        {
                            "date": bucket_date,
                            "total_orders": int(value["total_orders"]),
                            "valid_orders": int(value["valid_orders"]),
                            "valid_completed_orders": int(value["completed_orders"]),
                            "valid_completion_rate": safe_ratio(value["completed_orders"], value["valid_orders"]),
                            "completed_orders": int(value["completed_orders"]),
                            "cancelled_orders": int(value["cancelled_orders"]),
                            "completion_rate": safe_ratio(value["completed_orders"], value["total_orders"]),
                            "cancel_rate": safe_ratio(value["cancelled_orders"], value["total_orders"]),
                        }
                        for bucket_date, value in date_buckets.items()
                    ],
                    key=lambda item: item["date"],
                ),
                "region_ranking": sorted(
                    region_ranking_rows,
                    key=lambda item: item["completed_orders"],
                    reverse=True,
                )[:50],
                "partner_tier_stats": partner_tier_stats,
                "focus_partner_items": focus_partner_items,
                "risk_partner_items": risk_partner_items,
                "new_partner_performance": new_partner_performance[:60],
                "health_items": sorted(health_items, key=lambda item: item["total_score"], reverse=True)[:100],
                "applied_thresholds": {
                    "active_completed_threshold": active_completed_threshold,
                    "ranking_level": ranking_level,
                    "partner_tiers": tiers,
                    "day_count": day_count,
                },
            }
        )

    @app.get("/api/v1/admin/partners/fluctuation")
    def admin_partner_fluctuation(
        start_date: date | None = None,
        end_date: date | None = None,
        province: str | None = None,
        city: str | None = None,
        district: str | None = None,
        partner_id: str | None = None,
        large_city_daily_threshold: int | None = Query(default=None),
        large_city_change_abs: int | None = Query(default=None),
        large_city_change_pct: float | None = Query(default=None),
        medium_city_daily_threshold: int | None = Query(default=None),
        medium_city_change_abs: int | None = Query(default=None),
        medium_city_change_pct: float | None = Query(default=None),
        small_city_change_abs: int | None = Query(default=None),
        small_city_change_pct: float | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(AdsPartnerDayMetrics).order_by(AdsPartnerDayMetrics.partner_id, AdsPartnerDayMetrics.date)
            stmt = _apply_partner_day_filters(
                stmt,
                start_date=start_date,
                end_date=end_date,
                province=province,
                city=city,
                district=district,
                partner_id=partner_id,
            )
            rows = list(session.scalars(stmt))
        payload = build_partner_fluctuation_payload(
            rows,
            settings.alerts,
            overrides={
                "large_city_daily_threshold": large_city_daily_threshold,
                "large_city_change_abs": large_city_change_abs,
                "large_city_change_pct": large_city_change_pct,
                "medium_city_daily_threshold": medium_city_daily_threshold,
                "medium_city_change_abs": medium_city_change_abs,
                "medium_city_change_pct": medium_city_change_pct,
                "small_city_change_abs": small_city_change_abs,
                "small_city_change_pct": small_city_change_pct,
            },
        )
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                **payload,
            }
        )

    @app.get("/api/v1/admin/hourly")
    def admin_hourly(
        start_date: date | None = None,
        end_date: date | None = None,
        province: str | None = None,
        city: str | None = None,
        district: str | None = None,
        partner_id: str | None = None,
        scope: str = Query(default="all"),
        valid_cancel_threshold_minutes: int | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(DwdOrderDetail)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, province, city, district, partner_id)
            rows = list(session.scalars(stmt))

        _, hourly_summary = _build_hourly_metrics(rows, threshold=threshold, include_date=False)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "items": hourly_summary,
                "applied_thresholds": {
                    "scope": scope,
                    "valid_cancel_threshold_minutes": threshold,
                },
            }
        )

    @app.get("/api/v1/admin/health")
    def admin_health(
        start_date: date | None = None,
        end_date: date | None = None,
        province: str | None = None,
        city: str | None = None,
        district: str | None = None,
        partner_id: str | None = None,
    ):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(
                DwdOrderDetail.partner_id,
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                _sum_bool(DwdOrderDetail.is_valid_order.is_(True)).label("valid_orders"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_id), else_=None))).label("active_riders"),
                func.count(func.distinct(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.merchant_id), else_=None))).label("active_merchants"),
                func.sum(case(((DwdOrderDetail.is_completed.is_(True)) & (DwdOrderDetail.is_new_merchant_order.is_(True)), 1), else_=0)).label("new_merchant_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("actual_received_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
            ).where(DwdOrderDetail.partner_id.is_not(None))
            stmt = _apply_dwd_filters(stmt, start_date, end_date, province, city, district, partner_id)
            stmt = stmt.group_by(DwdOrderDetail.partner_id)
            rows = list(session.execute(stmt).mappings())

        day_count = _day_count(start_date, end_date, [])
        items = []
        for row in rows:
            valid_orders = float(row["valid_orders"] or 0.0)
            completed_orders = float(row["completed_orders"] or 0.0)
            items.append(
                {
                    "partner_id": row["partner_id"],
                    "partner_name": row["partner_name"] or row["partner_id"],
                    **_build_health_score(
                        {
                            "total_orders": float(row["total_orders"] or 0.0),
                            "valid_orders": valid_orders,
                            "completed_orders": completed_orders,
                            "cancelled_orders": float(row["cancelled_orders"] or 0.0),
                            "valid_cancel_orders": max(valid_orders - completed_orders, 0.0),
                            "active_riders": float(row["active_riders"] or 0.0),
                            "active_merchants": float(row["active_merchants"] or 0.0),
                            "new_merchant_orders": float(row["new_merchant_orders"] or 0.0),
                            "actual_received_total": float(row["actual_received_total"] or 0.0),
                            "partner_profit": float(row["partner_income_total"] or 0.0) - float(row["partner_subsidy_total"] or 0.0),
                        },
                        day_count=day_count,
                    ),
                }
            )

        items.sort(key=lambda item: item["total_score"], reverse=True)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "summary": _summarize_health_scores(items),
                "items": items[:100],
            }
        )

    def partner_rows(partner_id: str, start_date: date | None, end_date: date | None):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            rows = list(
                session.scalars(
                    select(AdsPartnerDayMetrics).where(AdsPartnerDayMetrics.partner_id == partner_id).order_by(AdsPartnerDayMetrics.date)
                )
            )
        filtered = _filter_by_date(rows, start_date, end_date)
        if not filtered:
            raise HTTPException(status_code=404, detail="未找到该合伙人的城市数据")
        return info, filtered

    @app.get("/api/v1/partner/{partner_id}/overview")
    def partner_overview(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        active_completed_threshold: int = Query(default=1, ge=1),
        valid_cancel_threshold_minutes: int | None = Query(default=None),
    ):
        info, rows = partner_rows(partner_id, start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            dwd_stmt = select(DwdOrderDetail)
            dwd_stmt = _apply_dwd_filters(dwd_stmt, start_date, end_date, partner_id=partner_id)
            dwd_rows = list(session.scalars(dwd_stmt))
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
        summary = defaultdict(float)
        for row in rows:
            summary["total_orders"] += row.total_orders
            summary["valid_orders"] += row.valid_orders
            summary["completed_orders"] += row.completed_orders
            summary["cancelled_orders"] += row.cancelled_orders
            summary["hq_subsidy_total"] += row.hq_subsidy_total
            summary["partner_subsidy_total"] += row.partner_subsidy_total
            summary["new_rider_orders"] += row.new_rider_orders
            summary["new_merchant_orders"] += row.new_merchant_orders

        with session_scope(session_factory) as session:
            active_riders = _count_active_entities(session, DwdOrderDetail.rider_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            active_merchants = _count_active_entities(session, DwdOrderDetail.merchant_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            new_riders = _count_new_entities(session, DwdOrderDetail.rider_id, DwdOrderDetail.is_new_rider_order, start_date, end_date, partner_id=partner_id)
            new_merchants = _count_new_entities(session, DwdOrderDetail.merchant_id, DwdOrderDetail.is_new_merchant_order, start_date, end_date, partner_id=partner_id)
            amount_stmt = select(
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("completed_amount_paid"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_income), else_=0.0)).label("rider_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
                func.sum(case((((DwdOrderDetail.is_cancelled.is_(True)) & (DwdOrderDetail.is_paid.is_(True)) & (DwdOrderDetail.pay_cancel_minutes > threshold)), 1), else_=0)).label("valid_cancel_orders"),
            )
            amount_stmt = _apply_dwd_filters(amount_stmt, start_date, end_date, partner_id=partner_id)
            amount_row = session.execute(amount_stmt).mappings().first() or {
                "completed_amount_paid": 0.0,
                "rider_income_total": 0.0,
                "partner_income_total": 0.0,
                "partner_subsidy_total": 0.0,
                "valid_cancel_orders": 0,
            }

        latest = rows[-1]
        day_count = _day_count(start_date, end_date, [item.date for item in rows if item.date])
        return api_response(
            build_partner_overview_payload(
                info=info,
                partner_id=partner_id,
                latest_row=latest,
                rows=rows,
                dwd_rows=dwd_rows,
                summary=summary,
                active_riders=active_riders,
                active_merchants=active_merchants,
                new_riders=new_riders,
                new_merchants=new_merchants,
                amount_row=amount_row,
                threshold=threshold,
                sla_minutes=sla_minutes,
                active_completed_threshold=active_completed_threshold,
                day_count=day_count,
                calc_duration_minutes=_calc_duration_minutes,
                safe_ratio=safe_ratio,
                calc_efficiency=_calc_efficiency,
                build_order_summary=_build_order_summary,
                build_health_score=_build_health_score,
            )
        )

    @app.get("/api/v1/partner/{partner_id}/health")
    def partner_health(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        active_completed_threshold: int = Query(default=1, ge=1),
        valid_cancel_threshold_minutes: int | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            active_riders = _count_active_entities(session, DwdOrderDetail.rider_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            active_merchants = _count_active_entities(session, DwdOrderDetail.merchant_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            stmt = select(
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                func.sum(
                    case(
                        (
                            (DwdOrderDetail.is_completed.is_(True))
                            | (
                                (DwdOrderDetail.is_cancelled.is_(True))
                                & (DwdOrderDetail.is_paid.is_(True))
                                & (DwdOrderDetail.pay_cancel_minutes > threshold)
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("valid_orders"),
                func.sum(case((((DwdOrderDetail.is_cancelled.is_(True)) & (DwdOrderDetail.is_paid.is_(True)) & (DwdOrderDetail.pay_cancel_minutes > threshold)), 1), else_=0)).label("valid_cancel_orders"),
                func.sum(case(((DwdOrderDetail.is_completed.is_(True)) & (DwdOrderDetail.is_new_merchant_order.is_(True)), 1), else_=0)).label("new_merchant_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.amount_paid), else_=0.0)).label("actual_received_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_income), else_=0.0)).label("partner_income_total"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.partner_subsidy_amount), else_=0.0)).label("partner_subsidy_total"),
            )
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            row = session.execute(stmt).mappings().first() or {}

        day_count = _day_count(start_date, end_date, [])
        return api_response(
            build_partner_health_payload(
                info=info,
                partner_id=partner_id,
                row=row,
                active_riders=active_riders,
                active_merchants=active_merchants,
                day_count=day_count,
                threshold=threshold,
                active_completed_threshold=active_completed_threshold,
                build_health_score=_build_health_score,
            )
        )

    @app.get("/api/v1/partner/{partner_id}/daily")
    def partner_daily(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        valid_cancel_threshold_minutes: int | None = Query(default=None),
    ):
        info, _ = partner_rows(partner_id, start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            stmt = select(DwdOrderDetail)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            dwd_rows = list(session.scalars(stmt))
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
        return api_response(
            build_partner_daily_payload(
                info=info,
                dwd_rows=dwd_rows,
                threshold=threshold,
                sla_minutes=sla_minutes,
                calc_duration_minutes=_calc_duration_minutes,
                safe_ratio=safe_ratio,
            )
        )

    @app.get("/api/v1/partner/{partner_id}/hourly")
    def partner_hourly(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        valid_cancel_threshold_minutes: int | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
            stmt = select(DwdOrderDetail)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            rows = list(session.scalars(stmt))
        items, hourly_summary = _build_hourly_metrics(rows, threshold=threshold, include_date=True)
        for item in items:
            item["sla_minutes"] = sla_minutes
        for item in hourly_summary:
            item["sla_minutes"] = sla_minutes
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "items": items,
                "hourly_summary": hourly_summary,
                "applied_thresholds": {
                    "valid_cancel_threshold_minutes": threshold,
                    "sla_minutes": sla_minutes,
                },
            }
        )

    @app.get("/api/v1/partner/{partner_id}/riders")
    def partner_riders(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        new_flag: str = Query(default="all"),
        rider_tiers: str | None = Query(default=None),
    ):
        _validate_query_window(start_date, end_date)
        info, _ = partner_rows(partner_id, start_date, end_date)
        tiers = _parse_generic_tiers(rider_tiers, _default_rider_tiers())
        with session_scope(session_factory) as session:
            daily_stmt = select(
                DwdOrderDetail.order_date.label("date"),
                DwdOrderDetail.rider_id.label("rider_id"),
                func.max(RiderRoster.rider_name).label("roster_rider_name"),
                func.max(DwdOrderDetail.rider_name).label("dwd_rider_name"),
                func.max(RiderRoster.hire_date).label("hire_date"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                func.max(case((DwdOrderDetail.is_new_rider_order.is_(True), 1), else_=0)).label("is_new_rider"),
            ).select_from(DwdOrderDetail).join(RiderRoster, RiderRoster.rider_id == DwdOrderDetail.rider_id, isouter=True)
            daily_stmt = _apply_dwd_filters(daily_stmt, start_date, end_date, partner_id=partner_id)
            daily_stmt = daily_stmt.where(DwdOrderDetail.rider_id.is_not(None)).group_by(DwdOrderDetail.order_date, DwdOrderDetail.rider_id)
            daily_rows = list(session.execute(daily_stmt).mappings())
        return api_response(
            build_partner_riders_payload(
                daily_rows=daily_rows,
                tiers=tiers,
                new_flag=new_flag,
                info=info,
                coalesce_text=_coalesce_text,
                to_iso_date=_to_iso_date,
            )
        )

    @app.get("/api/v1/partner/{partner_id}/merchants")
    def partner_merchants(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        new_flag: str = Query(default="all"),
    ):
        _validate_query_window(start_date, end_date)
        info, _ = partner_rows(partner_id, start_date, end_date)
        with session_scope(session_factory) as session:
            merchant_stmt = select(
                DwdOrderDetail.order_date.label("date"),
                DwdOrderDetail.merchant_id.label("merchant_id"),
                func.max(MerchantRoster.merchant_name).label("merchant_name"),
                func.max(MerchantRoster.register_date).label("register_date"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                _sum_bool(DwdOrderDetail.is_cancelled.is_(True)).label("cancelled_orders"),
                func.max(case((DwdOrderDetail.is_new_merchant_order.is_(True), 1), else_=0)).label("is_new_merchant"),
            ).select_from(DwdOrderDetail).join(MerchantRoster, MerchantRoster.merchant_id == DwdOrderDetail.merchant_id, isouter=True)
            merchant_stmt = _apply_dwd_filters(merchant_stmt, start_date, end_date, partner_id=partner_id)
            merchant_stmt = merchant_stmt.where(DwdOrderDetail.merchant_id.is_not(None)).group_by(DwdOrderDetail.order_date, DwdOrderDetail.merchant_id)
            merchant_rows = list(session.execute(merchant_stmt).mappings())
        return api_response(
            build_partner_merchants_payload(
                merchant_rows=merchant_rows,
                new_flag=new_flag,
                info=info,
                to_iso_date=_to_iso_date,
            )
        )

    @app.get("/api/v1/partner/{partner_id}/merchant-like-users")
    def partner_merchant_like_users(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        merchant_like_threshold: int = Query(default=20, ge=1),
    ):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            items = build_merchant_like_users(
                session,
                partner_id=partner_id,
                start_date=start_date,
                end_date=end_date,
                merchant_like_threshold=merchant_like_threshold,
                filter_by_date=_filter_by_date,
            )
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "merchant_like_threshold": merchant_like_threshold,
                "items": items,
            }
        )

    @app.get("/api/v1/partner/{partner_id}/new-riders")
    def partner_new_riders(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        response = partner_riders(partner_id=partner_id, start_date=start_date, end_date=end_date, new_flag="new", rider_tiers=None)
        response["data"] = {
            "data_version": response["data"]["data_version"],
            "latest_ready_month": response["data"]["latest_ready_month"],
            "daily": response["data"]["daily"],
            "items": response["data"]["items"],
        }
        return response

    @app.get("/api/v1/partner/{partner_id}/new-merchants")
    def partner_new_merchants(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        response = partner_merchants(partner_id=partner_id, start_date=start_date, end_date=end_date, new_flag="new")
        response["data"] = {
            "data_version": response["data"]["data_version"],
            "latest_ready_month": response["data"]["latest_ready_month"],
            "daily": response["data"]["daily"],
            "items": response["data"]["items"],
        }
        return response

    @app.get("/api/v1/partner/{partner_id}/income/riders")
    def partner_income_riders(
        partner_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(
                DwdOrderDetail.rider_id,
                func.max(RiderRoster.rider_name).label("roster_rider_name"),
                func.max(DwdOrderDetail.rider_name).label("dwd_rider_name"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), DwdOrderDetail.rider_income), else_=0.0)).label("rider_commission_total"),
            ).select_from(DwdOrderDetail).join(RiderRoster, RiderRoster.rider_id == DwdOrderDetail.rider_id, isouter=True)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            stmt = stmt.where(DwdOrderDetail.rider_id.is_not(None)).group_by(DwdOrderDetail.rider_id)
            rows = []
            for row in session.execute(stmt).mappings():
                completed_orders = int(row["completed_orders"] or 0)
                commission_total = float(row["rider_commission_total"] or 0.0)
                if completed_orders <= 0 and commission_total <= 0:
                    continue
                rows.append(
                    {
                        "rider_id": row["rider_id"],
                        "rider_name": _coalesce_text(row["roster_rider_name"], _coalesce_text(row["dwd_rider_name"], row["rider_id"])),
                        "completed_orders": completed_orders,
                        "rider_commission_total": round(commission_total, 2),
                        "rider_avg_commission": round(commission_total / completed_orders, 2) if completed_orders else 0.0,
                    }
                )
        rows.sort(key=lambda item: (item["rider_commission_total"], item["completed_orders"]), reverse=True)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "items": rows[:200],
            }
        )

    @app.get("/api/v1/partner/{partner_id}/sla")
    def get_partner_sla(partner_id: str):
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
            config = session.get(PartnerSlaConfig, partner_id)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "partner_id": partner_id,
                "sla_minutes": sla_minutes,
                "effective_date": _to_iso_date(config.effective_date) if config else None,
                "updated_at": config.updated_at.isoformat() if config and config.updated_at else None,
                "is_default": config is None,
            }
        )

    @app.post("/api/v1/partner/{partner_id}/sla")
    def set_partner_sla(
        partner_id: str,
        sla_minutes: int = Query(..., ge=1, le=240),
        effective_date: date | None = None,
    ):
        with session_scope(session_factory) as session:
            config = session.get(PartnerSlaConfig, partner_id)
            if not config:
                config = PartnerSlaConfig(partner_id=partner_id)
                session.add(config)
            config.sla_minutes = int(sla_minutes)
            config.effective_date = effective_date
            session.flush()
            updated_at = config.updated_at
        return api_response(
            {
                "partner_id": partner_id,
                "sla_minutes": int(sla_minutes),
                "effective_date": _to_iso_date(effective_date),
                "updated_at": updated_at.isoformat() if updated_at else None,
                "is_default": False,
            }
        )
    @app.get("/api/v1/direct/cancel-daily")
    def direct_cancel_daily(
        partner_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        valid_cancel_threshold_minutes: int | None = Query(default=None),
        active_completed_threshold: int = Query(default=1, ge=1),
    ):
        _validate_query_window(start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
            stmt = select(DwdOrderDetail)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            rows = list(session.scalars(stmt))
            active_riders = _count_active_entities(session, DwdOrderDetail.rider_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            active_merchants = _count_active_entities(session, DwdOrderDetail.merchant_id, active_completed_threshold, start_date, end_date, partner_id=partner_id)
            new_riders = _count_new_entities(session, DwdOrderDetail.rider_id, DwdOrderDetail.is_new_rider_order, start_date, end_date, partner_id=partner_id)
            new_merchants = _count_new_entities(session, DwdOrderDetail.merchant_id, DwdOrderDetail.is_new_merchant_order, start_date, end_date, partner_id=partner_id)

        grouped = defaultdict(
            lambda: {
                "partner_id": partner_id,
                "partner_name": None,
                "total_orders": 0,
                "completed_orders": 0,
                "cancelled_orders": 0,
                "valid_orders": 0,
                "valid_cancel_orders": 0,
                "unaccepted_timeout_online_cancel_orders": 0,
                "unaccepted_timeout_offline_cancel_orders": 0,
                "unaccepted_timeout_cancel_orders": 0,
                "unaccepted_not_timeout_cancel_orders": 0,
                "unaccepted_cancel_orders": 0,
                "accepted_noliability_cancel_orders": 0,
                "unpaid_cancel_orders": 0,
                "completed_amount_paid": 0.0,
                "completed_rider_income": 0.0,
                "partner_income_total": 0.0,
                "partner_subsidy_total": 0.0,
                "hq_subsidy_total": 0.0,
                "on_time_orders": 0,
                "sla_on_time_orders": 0,
                "sla_overtime_orders": 0,
                "sla_completed_base": 0,
            }
        )
        summary = defaultdict(float)
        for row in rows:
            if not row.order_date:
                continue
            bucket = grouped[row.order_date.isoformat()]
            bucket["partner_id"] = row.partner_id
            bucket["partner_name"] = row.partner_name or bucket["partner_name"]
            bucket["total_orders"] += 1
            if row.is_completed:
                bucket["completed_orders"] += 1
                bucket["completed_amount_paid"] += float(row.amount_paid or 0.0)
                bucket["completed_rider_income"] += float(row.rider_income or 0.0)
                bucket["partner_income_total"] += float(row.partner_income or 0.0)
                bucket["partner_subsidy_total"] += float(row.partner_subsidy_amount or 0.0)
                bucket["hq_subsidy_total"] += float(row.hq_subsidy_amount or 0.0)
                duration_minutes = _calc_duration_minutes(row.accept_time, row.complete_time)
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
            is_valid_order = bool(row.is_completed or is_valid_cancel)
            is_timeout_cancel = bool(row.is_cancelled and (row.order_elapsed_minutes_to_cancel or 0) > threshold)
            if is_valid_order:
                bucket["valid_orders"] += 1
            if is_valid_cancel:
                bucket["valid_cancel_orders"] += 1
            if row.is_cancelled and row.is_unaccepted_cancel:
                bucket["unaccepted_cancel_orders"] += 1
                if is_timeout_cancel:
                    bucket["unaccepted_timeout_cancel_orders"] += 1
                    if row.service_online_flag:
                        bucket["unaccepted_timeout_online_cancel_orders"] += 1
                    else:
                        bucket["unaccepted_timeout_offline_cancel_orders"] += 1
                else:
                    bucket["unaccepted_not_timeout_cancel_orders"] += 1
            if row.is_cancelled and row.is_accepted_cancel and row.is_rider_noliability_cancel:
                bucket["accepted_noliability_cancel_orders"] += 1
            if row.is_cancelled and not row.is_paid:
                bucket["unpaid_cancel_orders"] += 1

        items = []
        for bucket_date, bucket in sorted(grouped.items()):
            summary["total_orders"] += bucket["total_orders"]
            summary["completed_orders"] += bucket["completed_orders"]
            summary["cancelled_orders"] += bucket["cancelled_orders"]
            summary["valid_orders"] += bucket["valid_orders"]
            summary["valid_cancel_orders"] += bucket["valid_cancel_orders"]
            summary["unaccepted_timeout_online_cancel_orders"] += bucket["unaccepted_timeout_online_cancel_orders"]
            summary["completed_amount_paid"] += bucket["completed_amount_paid"]
            summary["completed_rider_income"] += bucket["completed_rider_income"]
            summary["partner_income_total"] += bucket["partner_income_total"]
            summary["partner_subsidy_total"] += bucket["partner_subsidy_total"]
            summary["hq_subsidy_total"] += bucket["hq_subsidy_total"]
            summary["on_time_orders"] += bucket["on_time_orders"]
            summary["sla_on_time_orders"] += bucket["sla_on_time_orders"]
            summary["sla_overtime_orders"] += bucket["sla_overtime_orders"]
            summary["sla_completed_base"] += bucket["sla_completed_base"]
            items.append(
                {
                    "date": bucket_date,
                    **bucket,
                    "valid_completed_orders": bucket["completed_orders"],
                    "valid_completion_rate": safe_ratio(bucket["completed_orders"], bucket["valid_orders"]),
                    "completion_rate": safe_ratio(bucket["completed_orders"], bucket["total_orders"]),
                    "cancel_rate": safe_ratio(bucket["cancelled_orders"], bucket["total_orders"]),
                    "valid_cancel_rate": safe_ratio(bucket["valid_cancel_orders"], bucket["valid_orders"]),
                    "unaccepted_timeout_online_cancel_rate": safe_ratio(bucket["unaccepted_timeout_online_cancel_orders"], bucket["total_orders"]),
                    "avg_ticket_price": round(bucket["completed_amount_paid"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
                    "rider_avg_commission": round(bucket["completed_rider_income"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
                    "rider_avg_income": round(bucket["completed_rider_income"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
                    "partner_income_total": round(bucket["partner_income_total"], 2),
                    "partner_subsidy_total": round(bucket["partner_subsidy_total"], 2),
                    "hq_subsidy_total": round(bucket["hq_subsidy_total"], 2),
                    "partner_profit": round(bucket["partner_income_total"] - bucket["partner_subsidy_total"], 2),
                    "on_time_rate": safe_ratio(bucket["on_time_orders"], bucket["sla_completed_base"]),
                    "sla_minutes": sla_minutes,
                    "sla_on_time_rate": safe_ratio(bucket["sla_on_time_orders"], bucket["sla_completed_base"]),
                    "sla_overtime_rate": safe_ratio(bucket["sla_overtime_orders"], bucket["sla_completed_base"]),
                }
            )

        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "summary": {
                    "total_orders": int(summary["total_orders"]),
                    "valid_orders": int(summary["valid_orders"]),
                    "valid_completed_orders": int(summary["completed_orders"]),
                    "cancelled_orders": int(summary["cancelled_orders"]),
                    "completion_rate": safe_ratio(summary["completed_orders"], summary["total_orders"]),
                    "cancel_rate": safe_ratio(summary["cancelled_orders"], summary["total_orders"]),
                    "valid_completion_rate": safe_ratio(summary["completed_orders"], summary["valid_orders"]),
                    "completed_orders": int(summary["completed_orders"]),
                    "valid_cancel_orders": int(summary["valid_cancel_orders"]),
                    "valid_cancel_rate": safe_ratio(summary["valid_cancel_orders"], summary["valid_orders"]),
                    "active_riders": active_riders,
                    "new_riders": new_riders,
                    "active_merchants": active_merchants,
                    "new_merchants": new_merchants,
                    "hq_subsidy_total": round(summary["hq_subsidy_total"], 2),
                    "partner_subsidy_total": round(summary["partner_subsidy_total"], 2),
                    "efficiency": _calc_efficiency(summary["completed_orders"], active_riders),
                    "avg_ticket_price": round(summary["completed_amount_paid"] / summary["completed_orders"], 2) if summary["completed_orders"] else 0.0,
                    "rider_avg_commission": round(summary["completed_rider_income"] / summary["completed_orders"], 2) if summary["completed_orders"] else 0.0,
                    "rider_avg_income": round(summary["completed_rider_income"] / summary["completed_orders"], 2) if summary["completed_orders"] else 0.0,
                    "actual_received_total": round(summary["completed_amount_paid"], 2),
                    "rider_commission_total": round(summary["completed_rider_income"], 2),
                    "partner_income_total": round(summary["partner_income_total"], 2),
                    "partner_profit": round(summary["partner_income_total"] - summary["partner_subsidy_total"], 2),
                    "on_time_orders": int(summary["on_time_orders"]),
                    "on_time_rate": safe_ratio(summary["on_time_orders"], summary["sla_completed_base"]),
                    "sla_minutes": sla_minutes,
                    "sla_on_time_orders": int(summary["sla_on_time_orders"]),
                    "sla_overtime_orders": int(summary["sla_overtime_orders"]),
                    "sla_on_time_rate": safe_ratio(summary["sla_on_time_orders"], summary["sla_completed_base"]),
                    "sla_overtime_rate": safe_ratio(summary["sla_overtime_orders"], summary["sla_completed_base"]),
                    "unaccepted_timeout_online_cancel_orders": int(summary["unaccepted_timeout_online_cancel_orders"]),
                    "unaccepted_timeout_online_cancel_rate": safe_ratio(summary["unaccepted_timeout_online_cancel_orders"], summary["total_orders"]),
                },
                "items": items,
                "applied_thresholds": {
                    "valid_cancel_threshold_minutes": threshold,
                    "active_completed_threshold": active_completed_threshold,
                    "sla_minutes": sla_minutes,
                },
            }
        )

    @app.get("/api/v1/direct/hourly")
    def direct_hourly(
        partner_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        valid_cancel_threshold_minutes: int | None = Query(default=None),
        active_completed_threshold: int = Query(default=1, ge=1),
    ):
        _validate_query_window(start_date, end_date)
        threshold = valid_cancel_threshold_minutes or settings.business.valid_order_cancel_threshold_minutes
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            sla_minutes = _get_partner_sla_minutes(session, partner_id)
            stmt = select(DwdOrderDetail)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            rows = list(session.scalars(stmt))

        per_date_hour = defaultdict(
            lambda: {
                "unpaid_orders": 0,
                "unaccepted_cancel_orders": 0,
                "accepted_cancel_orders": 0,
                "completed_orders": 0,
                "cancelled_orders": 0,
                "total_orders": 0,
                "valid_orders": 0,
                "valid_cancel_orders": 0,
                "accepted_riders": set(),
                "parttime_completed_orders": 0,
                "parttime_riders": set(),
                "fulltime_completed_orders": 0,
                "fulltime_riders": set(),
                "completed_amount_paid": 0.0,
                "completed_rider_income": 0.0,
                "on_time_orders": 0,
                "sla_on_time_orders": 0,
                "sla_overtime_orders": 0,
                "sla_completed_base": 0,
            }
        )

        for row in rows:
            if row.order_date is None or row.order_hour is None:
                continue
            bucket = per_date_hour[(row.order_date.isoformat(), row.order_hour)]
            bucket["total_orders"] += 1
            if row.is_completed:
                bucket["completed_orders"] += 1
                bucket["completed_amount_paid"] += float(row.amount_paid or 0.0)
                bucket["completed_rider_income"] += float(row.rider_income or 0.0)
                duration_minutes = _calc_duration_minutes(row.accept_time, row.complete_time)
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
            if row.is_cancelled and not row.is_paid:
                bucket["unpaid_orders"] += 1
            if row.is_cancelled and row.is_unaccepted_cancel:
                bucket["unaccepted_cancel_orders"] += 1
            if row.is_cancelled and row.is_accepted_cancel:
                bucket["accepted_cancel_orders"] += 1
            is_valid_cancel = bool(row.is_cancelled and row.is_paid and (row.pay_cancel_minutes or 0) > threshold)
            if row.is_completed or is_valid_cancel:
                bucket["valid_orders"] += 1
            if is_valid_cancel:
                bucket["valid_cancel_orders"] += 1
            if row.accept_time and row.rider_id:
                bucket["accepted_riders"].add(row.rider_id)
            if row.is_completed and row.employment_type == "parttime":
                bucket["parttime_completed_orders"] += 1
                if row.rider_id:
                    bucket["parttime_riders"].add(row.rider_id)
            if row.is_completed and row.employment_type == "fulltime":
                bucket["fulltime_completed_orders"] += 1
                if row.rider_id:
                    bucket["fulltime_riders"].add(row.rider_id)

        items = []
        by_hour = defaultdict(lambda: defaultdict(float))
        for (bucket_date, hour), bucket in sorted(per_date_hour.items()):
            item = {
                "date": bucket_date,
                "hour": hour,
                "unpaid_orders": bucket["unpaid_orders"],
                "unaccepted_cancel_orders": bucket["unaccepted_cancel_orders"],
                "accepted_cancel_orders": bucket["accepted_cancel_orders"],
                "completed_orders": bucket["completed_orders"],
                "delivered_orders": bucket["completed_orders"],
                "cancelled_orders": bucket["cancelled_orders"],
                "total_orders": bucket["total_orders"],
                "valid_orders": bucket["valid_orders"],
                "valid_completed_orders": bucket["completed_orders"],
                "valid_completion_rate": safe_ratio(bucket["completed_orders"], bucket["valid_orders"]),
                "valid_cancel_orders": bucket["valid_cancel_orders"],
                "valid_cancel_rate": safe_ratio(bucket["valid_cancel_orders"], bucket["valid_orders"]),
                "accepted_rider_count": len(bucket["accepted_riders"]),
                "parttime_completed_orders": bucket["parttime_completed_orders"],
                "parttime_rider_count": len(bucket["parttime_riders"]),
                "fulltime_completed_orders": bucket["fulltime_completed_orders"],
                "fulltime_rider_count": len(bucket["fulltime_riders"]),
                "completed_amount_paid": bucket["completed_amount_paid"],
                "completed_rider_income": bucket["completed_rider_income"],
                "on_time_orders": bucket["on_time_orders"],
                "on_time_rate": safe_ratio(bucket["on_time_orders"], bucket["sla_completed_base"]),
                "sla_minutes": sla_minutes,
                "sla_on_time_orders": bucket["sla_on_time_orders"],
                "sla_overtime_orders": bucket["sla_overtime_orders"],
                "sla_on_time_rate": safe_ratio(bucket["sla_on_time_orders"], bucket["sla_completed_base"]),
                "sla_overtime_rate": safe_ratio(bucket["sla_overtime_orders"], bucket["sla_completed_base"]),
                "parttime_efficiency": safe_ratio(bucket["parttime_completed_orders"], len(bucket["parttime_riders"])),
                "fulltime_efficiency": safe_ratio(bucket["fulltime_completed_orders"], len(bucket["fulltime_riders"])),
                "completion_rate": safe_ratio(bucket["completed_orders"], bucket["total_orders"]),
                "cancel_rate": safe_ratio(bucket["cancelled_orders"], bucket["total_orders"]),
                "avg_ticket_price": round(bucket["completed_amount_paid"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
                "rider_avg_commission": round(bucket["completed_rider_income"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
                "rider_avg_income": round(bucket["completed_rider_income"] / bucket["completed_orders"], 2) if bucket["completed_orders"] else 0.0,
            }
            items.append(item)
            for key, value in item.items():
                if key in {"date", "hour", "sla_minutes", "avg_ticket_price", "rider_avg_commission", "rider_avg_income", "parttime_efficiency", "fulltime_efficiency", "completion_rate", "cancel_rate", "valid_completion_rate", "valid_cancel_rate", "on_time_rate", "sla_on_time_rate", "sla_overtime_rate"}:
                    continue
                by_hour[hour][key] += value

        hourly_summary = []
        for hour in sorted(by_hour):
            values = by_hour[hour]
            hourly_summary.append(
                {
                    "hour": hour,
                    "unpaid_orders": int(values["unpaid_orders"]),
                    "unaccepted_cancel_orders": int(values["unaccepted_cancel_orders"]),
                    "accepted_cancel_orders": int(values["accepted_cancel_orders"]),
                    "completed_orders": int(values["completed_orders"]),
                    "delivered_orders": int(values["completed_orders"]),
                    "cancelled_orders": int(values["cancelled_orders"]),
                    "total_orders": int(values["total_orders"]),
                    "valid_orders": int(values["valid_orders"]),
                    "valid_completed_orders": int(values["completed_orders"]),
                    "valid_completion_rate": safe_ratio(values["completed_orders"], values["valid_orders"]),
                    "valid_cancel_orders": int(values["valid_cancel_orders"]),
                    "valid_cancel_rate": safe_ratio(values["valid_cancel_orders"], values["valid_orders"]),
                    "accepted_rider_count": int(values["accepted_rider_count"]),
                    "parttime_completed_orders": int(values["parttime_completed_orders"]),
                    "parttime_rider_count": int(values["parttime_rider_count"]),
                    "fulltime_completed_orders": int(values["fulltime_completed_orders"]),
                    "fulltime_rider_count": int(values["fulltime_rider_count"]),
                    "on_time_orders": int(values["on_time_orders"]),
                    "on_time_rate": safe_ratio(values["on_time_orders"], values["sla_completed_base"]),
                    "sla_minutes": sla_minutes,
                    "sla_on_time_orders": int(values["sla_on_time_orders"]),
                    "sla_overtime_orders": int(values["sla_overtime_orders"]),
                    "sla_on_time_rate": safe_ratio(values["sla_on_time_orders"], values["sla_completed_base"]),
                    "sla_overtime_rate": safe_ratio(values["sla_overtime_orders"], values["sla_completed_base"]),
                    "parttime_efficiency": safe_ratio(values["parttime_completed_orders"], values["parttime_rider_count"]),
                    "fulltime_efficiency": safe_ratio(values["fulltime_completed_orders"], values["fulltime_rider_count"]),
                    "completion_rate": safe_ratio(values["completed_orders"], values["total_orders"]),
                    "cancel_rate": safe_ratio(values["cancelled_orders"], values["total_orders"]),
                    "avg_ticket_price": round(values["completed_amount_paid"] / values["completed_orders"], 2) if values["completed_orders"] else 0.0,
                    "rider_avg_commission": round(values["completed_rider_income"] / values["completed_orders"], 2) if values["completed_orders"] else 0.0,
                    "rider_avg_income": round(values["completed_rider_income"] / values["completed_orders"], 2) if values["completed_orders"] else 0.0,
                }
            )

        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "items": items,
                "hourly_summary": hourly_summary,
                "applied_thresholds": {
                    "valid_cancel_threshold_minutes": threshold,
                    "active_completed_threshold": active_completed_threshold,
                    "sla_minutes": sla_minutes,
                },
            }
        )

    @app.get("/api/v1/direct/new-riders")
    def direct_new_riders(partner_id: str | None = None, start_date: date | None = None, end_date: date | None = None):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(
                DwdOrderDetail.partner_id,
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                DwdOrderDetail.rider_id,
                func.max(RiderRoster.rider_name).label("roster_rider_name"),
                func.max(DwdOrderDetail.rider_name).label("dwd_rider_name"),
                func.max(RiderRoster.hire_date).label("hire_date"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
            ).select_from(DwdOrderDetail).join(RiderRoster, RiderRoster.rider_id == DwdOrderDetail.rider_id, isouter=True)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            stmt = stmt.where(DwdOrderDetail.is_new_rider_order.is_(True), DwdOrderDetail.rider_id.is_not(None)).group_by(DwdOrderDetail.partner_id, DwdOrderDetail.rider_id)
            rows = list(session.execute(stmt).mappings())
        return api_response(
            build_direct_new_riders_payload(
                rows=rows,
                info=info,
                coalesce_text=_coalesce_text,
                to_iso_date=_to_iso_date,
            )
        )

    @app.get("/api/v1/direct/new-merchants")
    def direct_new_merchants(partner_id: str | None = None, start_date: date | None = None, end_date: date | None = None):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(
                DwdOrderDetail.partner_id,
                func.max(DwdOrderDetail.partner_name).label("partner_name"),
                DwdOrderDetail.merchant_id,
                func.max(MerchantRoster.merchant_name).label("merchant_name"),
                func.max(MerchantRoster.register_date).label("register_date"),
                func.count().label("total_orders"),
                _sum_bool(DwdOrderDetail.is_completed.is_(True)).label("completed_orders"),
            ).select_from(DwdOrderDetail).join(MerchantRoster, MerchantRoster.merchant_id == DwdOrderDetail.merchant_id, isouter=True)
            stmt = _apply_dwd_filters(stmt, start_date, end_date, partner_id=partner_id)
            stmt = stmt.where(DwdOrderDetail.is_new_merchant_order.is_(True), DwdOrderDetail.merchant_id.is_not(None)).group_by(DwdOrderDetail.partner_id, DwdOrderDetail.merchant_id)
            rows = list(session.execute(stmt).mappings())
        return api_response(
            build_direct_new_merchants_payload(
                rows=rows,
                info=info,
                to_iso_date=_to_iso_date,
                safe_ratio=safe_ratio,
            )
        )

    @app.get("/api/v1/direct/merchant-comparison")
    def direct_merchant_comparison(
        partner_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        baseline_start: date | None = None,
        baseline_end: date | None = None,
        compare_start: date | None = None,
        compare_end: date | None = None,
    ):
        _validate_query_window(start_date, end_date)
        baseline_window, current_window = _resolve_compare_periods(start_date, end_date, baseline_start, baseline_end, compare_start, compare_end)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(AdsDirectMerchantDayMetrics)
            if partner_id:
                stmt = stmt.where(AdsDirectMerchantDayMetrics.partner_id == partner_id)
            rows = list(session.scalars(stmt))

        merged: dict[str, dict[str, Any]] = {}
        for row in rows:
            period = None
            if _period_contains(row.date, baseline_window):
                period = "baseline"
            elif _period_contains(row.date, current_window):
                period = "current"
            if not period:
                continue

            key = f"{row.partner_id}|{row.merchant_id}"
            item = merged.setdefault(
                key,
                {
                    "partner_id": row.partner_id,
                    "partner_name": row.partner_name,
                    "merchant_id": row.merchant_id,
                    "merchant_name": row.merchant_name,
                    "baseline": defaultdict(float),
                    "current": defaultdict(float),
                },
            )
            bucket = item[period]
            bucket["unaccepted_cancel_orders"] += row.unaccepted_cancel_orders
            bucket["unaccepted_cancel_amount_paid"] += row.unaccepted_cancel_amount_paid
            bucket["accepted_cancel_orders"] += row.accepted_cancel_orders
            bucket["accepted_cancel_amount_paid"] += row.accepted_cancel_amount_paid
            bucket["completed_orders"] += row.completed_orders
            bucket["completed_amount_paid"] += row.completed_amount_paid
            bucket["total_orders"] += row.total_orders
            bucket["total_amount_paid"] += row.avg_amount_paid * row.total_orders

        items = []
        for item in merged.values():
            baseline_bucket = item["baseline"]
            current_bucket = item["current"]
            baseline_total = baseline_bucket["total_orders"]
            current_total = current_bucket["total_orders"]
            current_completion_rate = safe_ratio(current_bucket["completed_orders"], current_total)
            baseline_completion_rate = safe_ratio(baseline_bucket["completed_orders"], baseline_total)
            items.append(
                {
                    "partner_id": item["partner_id"],
                    "partner_name": item["partner_name"],
                    "merchant_id": item["merchant_id"],
                    "merchant_name": item["merchant_name"],
                    "baseline_total_orders": int(baseline_total),
                    "current_total_orders": int(current_total),
                    "change_total_orders": int(current_total - baseline_total),
                    "baseline_completion_rate": baseline_completion_rate,
                    "current_completion_rate": current_completion_rate,
                    "change_completion_rate": round(current_completion_rate - baseline_completion_rate, 4),
                    "current_avg_price": round(current_bucket["total_amount_paid"] / current_total, 2) if current_total else 0,
                    "baseline_avg_price": round(baseline_bucket["total_amount_paid"] / baseline_total, 2) if baseline_total else 0,
                    "current_unaccepted_cancel_orders": int(current_bucket["unaccepted_cancel_orders"]),
                    "current_unaccepted_avg_price": round(current_bucket["unaccepted_cancel_amount_paid"] / current_bucket["unaccepted_cancel_orders"], 2) if current_bucket["unaccepted_cancel_orders"] else 0,
                    "current_accepted_cancel_orders": int(current_bucket["accepted_cancel_orders"]),
                    "current_accepted_avg_price": round(current_bucket["accepted_cancel_amount_paid"] / current_bucket["accepted_cancel_orders"], 2) if current_bucket["accepted_cancel_orders"] else 0,
                    "current_completed_orders": int(current_bucket["completed_orders"]),
                    "current_completed_avg_price": round(current_bucket["completed_amount_paid"] / current_bucket["completed_orders"], 2) if current_bucket["completed_orders"] else 0,
                }
            )

        items.sort(key=lambda row: (row["current_completed_orders"], row["current_total_orders"]), reverse=True)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "baseline_period": {
                    "start_date": baseline_window[0].isoformat() if baseline_window[0] else None,
                    "end_date": baseline_window[1].isoformat() if baseline_window[1] else None,
                },
                "current_period": {
                    "start_date": current_window[0].isoformat() if current_window[0] else None,
                    "end_date": current_window[1].isoformat() if current_window[1] else None,
                },
                "items": items[:100],
            }
        )

    @app.get("/api/v1/direct/order-sources")
    def direct_order_sources(
        partner_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        baseline_start: date | None = None,
        baseline_end: date | None = None,
        compare_start: date | None = None,
        compare_end: date | None = None,
    ):
        _validate_query_window(start_date, end_date)
        baseline_window, current_window = _resolve_compare_periods(start_date, end_date, baseline_start, baseline_end, compare_start, compare_end)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(AdsDirectOrderSourceDayMetrics)
            if partner_id:
                stmt = stmt.where(AdsDirectOrderSourceDayMetrics.partner_id == partner_id)
            rows = list(session.scalars(stmt))

        merged: dict[str, dict[str, Any]] = {}
        for row in rows:
            period = None
            if _period_contains(row.date, baseline_window):
                period = "baseline"
            elif _period_contains(row.date, current_window):
                period = "current"
            if not period:
                continue
            item = merged.setdefault(
                row.order_source,
                {
                    "order_source": row.order_source,
                    "baseline": defaultdict(float),
                    "current": defaultdict(float),
                },
            )
            bucket = item[period]
            bucket["unpaid_orders"] += row.unpaid_orders
            bucket["unaccepted_cancel_orders"] += row.unaccepted_cancel_orders
            bucket["accepted_cancel_orders"] += row.accepted_cancel_orders
            bucket["completed_orders"] += row.completed_orders
            bucket["total_orders"] += row.total_orders

        with session_scope(session_factory) as session:
            valid_stmt = select(
                DwdOrderDetail.order_source,
                func.sum(case((DwdOrderDetail.is_valid_order.is_(True), 1), else_=0)).label("valid_orders"),
                func.sum(case((DwdOrderDetail.is_completed.is_(True), 1), else_=0)).label("valid_completed_orders"),
            )
            valid_stmt = _apply_dwd_filters(valid_stmt, start_date=current_window[0], end_date=current_window[1], partner_id=partner_id)
            valid_stmt = valid_stmt.group_by(DwdOrderDetail.order_source)
            current_valid_map = {
                row["order_source"] or "未知": row
                for row in session.execute(valid_stmt).mappings()
            }

        items = []
        for item in merged.values():
            baseline_bucket = item["baseline"]
            current_bucket = item["current"]
            source_key = item["order_source"] or "未知"
            valid_bucket = current_valid_map.get(source_key, {})
            items.append(
                {
                    "order_source": source_key,
                    "baseline_total_orders": int(baseline_bucket["total_orders"]),
                    "current_total_orders": int(current_bucket["total_orders"]),
                    "change_total_orders": int(current_bucket["total_orders"] - baseline_bucket["total_orders"]),
                    "baseline_unaccepted_cancel_orders": int(baseline_bucket["unaccepted_cancel_orders"]),
                    "current_unaccepted_cancel_orders": int(current_bucket["unaccepted_cancel_orders"]),
                    "change_unaccepted_cancel_orders": int(current_bucket["unaccepted_cancel_orders"] - baseline_bucket["unaccepted_cancel_orders"]),
                    "current_completed_orders": int(current_bucket["completed_orders"]),
                    "current_cancelled_orders": int(current_bucket["unaccepted_cancel_orders"] + current_bucket["accepted_cancel_orders"] + current_bucket["unpaid_orders"]),
                    "current_valid_orders": int(valid_bucket.get("valid_orders") or 0),
                    "current_valid_completed_orders": int(valid_bucket.get("valid_completed_orders") or 0),
                }
            )
        items.sort(key=lambda row: row["current_total_orders"], reverse=True)
        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "baseline_period": {
                    "start_date": baseline_window[0].isoformat() if baseline_window[0] else None,
                    "end_date": baseline_window[1].isoformat() if baseline_window[1] else None,
                },
                "current_period": {
                    "start_date": current_window[0].isoformat() if current_window[0] else None,
                    "end_date": current_window[1].isoformat() if current_window[1] else None,
                },
                "items": items,
            }
        )

    @app.get("/api/v1/direct/coupons")
    def direct_coupons(partner_id: str | None = None, start_date: date | None = None, end_date: date | None = None):
        _validate_query_window(start_date, end_date)
        with session_scope(session_factory) as session:
            info = get_latest_import_info(session)
            stmt = select(AdsDirectCouponMetrics).order_by(AdsDirectCouponMetrics.date.desc())
            if partner_id:
                stmt = stmt.where(AdsDirectCouponMetrics.partner_id == partner_id)
            rows = list(session.scalars(stmt))

        rows = _filter_by_date(rows, start_date, end_date)
        summary = defaultdict(float)
        for row in rows:
            summary["coupon_order_count"] += row.coupon_order_count
            summary["hq_discount_total"] += row.hq_discount_total
            summary["discount_total"] += row.discount_total
            summary["total_discount"] += row.total_discount

        items = []
        if summary["coupon_order_count"] or summary["total_discount"]:
            items.append(
                {
                    "coupon_label": "全部优惠订单",
                    "coupon_order_count": int(summary["coupon_order_count"]),
                    "hq_discount_total": round(summary["hq_discount_total"], 2),
                    "discount_total": round(summary["discount_total"], 2),
                    "total_discount": round(summary["total_discount"], 2),
                }
            )

        return api_response(
            {
                "data_version": info.get("data_version"),
                "latest_ready_month": info.get("latest_ready_month"),
                "summary": {
                    "coupon_order_count": int(summary["coupon_order_count"]),
                    "hq_discount_total": round(summary["hq_discount_total"], 2),
                    "discount_total": round(summary["discount_total"], 2),
                    "total_discount": round(summary["total_discount"], 2),
                },
                "items": items,
            }
        )
    return app
