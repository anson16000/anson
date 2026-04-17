from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Callable

from sqlalchemy import select

from app.models import AdsPartnerUserMerchantMetrics


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
