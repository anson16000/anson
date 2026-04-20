from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Callable

from sqlalchemy import case, func, select

from app.models import AdsPartnerUserMerchantMetrics, DwdOrderDetail


def build_merchant_like_users(
    session,
    partner_id: str,
    start_date: date | None,
    end_date: date | None,
    merchant_like_threshold: int,
    filter_by_date: Callable[[list[Any], date | None, date | None], list[Any]],
) -> list[dict[str, Any]]:
    user_rows = list(
        session.scalars(
            select(AdsPartnerUserMerchantMetrics)
            .where(AdsPartnerUserMerchantMetrics.partner_id == partner_id)
            .order_by(AdsPartnerUserMerchantMetrics.date)
        )
    )
    user_rows = filter_by_date(user_rows, start_date, end_date)
    totals = defaultdict(int)
    for row in user_rows:
        totals[row.user_id] += row.completed_orders
    return sorted(
        [
            {"user_id": user_id, "completed_orders": completed_orders}
            for user_id, completed_orders in totals.items()
            if completed_orders >= merchant_like_threshold
        ],
        key=lambda item: item["completed_orders"],
        reverse=True,
    )[:20]


def build_partner_order_sources(
    session,
    partner_id: str,
    start_date: date | None,
    end_date: date | None,
    apply_dwd_filters: Callable[..., Any],
) -> dict[str, Any]:
    source_expr = func.coalesce(func.nullif(DwdOrderDetail.order_source, ""), "未知")
    stmt = select(
        source_expr.label("order_source"),
        func.count().label("total_orders"),
        func.sum(case((DwdOrderDetail.is_completed.is_(True), 1), else_=0)).label("completed_orders"),
        func.sum(case((DwdOrderDetail.is_cancelled.is_(True), 1), else_=0)).label("cancelled_orders"),
        func.sum(case((DwdOrderDetail.is_valid_order.is_(True), 1), else_=0)).label("valid_orders"),
        func.sum(
            case(
                ((DwdOrderDetail.is_valid_order.is_(True) & DwdOrderDetail.is_completed.is_(True)), 1),
                else_=0,
            )
        ).label("valid_completed_orders"),
    ).select_from(DwdOrderDetail)
    stmt = apply_dwd_filters(stmt, start_date=start_date, end_date=end_date, partner_id=partner_id)
    stmt = stmt.group_by(source_expr)
    rows = [
        {
            "order_source": row["order_source"] or "未知",
            "total_orders": int(row["total_orders"] or 0),
            "completed_orders": int(row["completed_orders"] or 0),
            "cancelled_orders": int(row["cancelled_orders"] or 0),
            "valid_orders": int(row["valid_orders"] or 0),
            "valid_completed_orders": int(row["valid_completed_orders"] or 0),
        }
        for row in session.execute(stmt).mappings()
    ]
    rows.sort(key=lambda item: (item["total_orders"], item["completed_orders"]), reverse=True)
    summary = {
        "total_orders": sum(item["total_orders"] for item in rows),
        "completed_orders": sum(item["completed_orders"] for item in rows),
        "valid_orders": sum(item["valid_orders"] for item in rows),
    }
    return {"items": rows, "summary": summary}
