from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import desc, func, select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings
from app.database import session_scope
from app.models import (
    AdsAdminDayMetrics,
    AdsPartnerDayMetrics,
    DwdOrderDetail,
    MerchantRoster,
    OrderDetailRaw,
    PartnerRoster,
    RiderRoster,
)
from app.pipeline import init_database


def main():
    settings = load_settings()
    _, session_factory = init_database(settings)
    with session_scope(session_factory) as session:
        min_order_date = session.scalar(select(func.min(DwdOrderDetail.order_date)))
        max_order_date = session.scalar(select(func.max(DwdOrderDetail.order_date)))
        print(
            {
                "raw_order_count": session.scalar(select(func.count()).select_from(OrderDetailRaw)) or 0,
                "rider_roster_count": session.scalar(select(func.count()).select_from(RiderRoster)) or 0,
                "merchant_roster_count": session.scalar(select(func.count()).select_from(MerchantRoster)) or 0,
                "partner_roster_count": session.scalar(select(func.count()).select_from(PartnerRoster)) or 0,
                "dwd_count": session.scalar(select(func.count()).select_from(DwdOrderDetail)) or 0,
                "ads_partner_day_count": session.scalar(select(func.count()).select_from(AdsPartnerDayMetrics)) or 0,
                "min_order_date": min_order_date.isoformat() if min_order_date else None,
                "max_order_date": max_order_date.isoformat() if max_order_date else None,
            }
        )

        overall = session.execute(
            select(
                func.sum(AdsAdminDayMetrics.total_orders),
                func.sum(AdsAdminDayMetrics.valid_orders),
                func.sum(AdsAdminDayMetrics.completed_orders),
                func.sum(AdsAdminDayMetrics.cancelled_orders),
            )
        ).one()
        print(
            {
                "admin_summary": {
                    "total_orders": int(overall[0] or 0),
                    "valid_orders": int(overall[1] or 0),
                    "completed_orders": int(overall[2] or 0),
                    "cancelled_orders": int(overall[3] or 0),
                }
            }
        )

        top_partners = session.execute(
            select(
                AdsPartnerDayMetrics.partner_id,
                AdsPartnerDayMetrics.partner_name,
                func.sum(AdsPartnerDayMetrics.completed_orders).label("completed_orders"),
                func.sum(AdsPartnerDayMetrics.cancelled_orders).label("cancelled_orders"),
            )
            .group_by(AdsPartnerDayMetrics.partner_id, AdsPartnerDayMetrics.partner_name)
            .order_by(desc("completed_orders"))
            .limit(10)
        ).all()
        print(
            {
                "top_partners": [
                    {
                        "partner_id": row[0],
                        "partner_name": row[1],
                        "completed_orders": int(row[2] or 0),
                        "cancelled_orders": int(row[3] or 0),
                    }
                    for row in top_partners
                ]
            }
        )

        sample_raw = session.scalar(select(OrderDetailRaw).limit(1))
        if sample_raw:
            print(
                {
                    "sample_order_id": sample_raw.order_id,
                    "sample_partner_id": sample_raw.partner_id,
                    "sample_status": sample_raw.order_status,
                    "sample_added_at": sample_raw.added_at,
                }
            )


if __name__ == "__main__":
    main()
