from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import func, select

ROOT = Path(r"F:\codex\delivery-dashboard")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings
from app.database import create_session_factory, session_scope
from app.models import AdsAdminDayMetrics, AdsAdminPartnerMetrics, AdsPartnerDayMetrics


def main() -> None:
    settings = load_settings()
    _, session_factory = create_session_factory(settings)
    with session_scope(session_factory) as session:
        admin_day = session.scalar(select(func.count()).select_from(AdsAdminDayMetrics)) or 0
        admin_partner = session.scalar(select(func.count()).select_from(AdsAdminPartnerMetrics)) or 0
        partner_day = session.scalar(select(func.count()).select_from(AdsPartnerDayMetrics)) or 0
        sample = session.execute(
            select(
                AdsAdminPartnerMetrics.date,
                AdsAdminPartnerMetrics.partner_id,
                AdsAdminPartnerMetrics.completed_orders,
            ).limit(10)
        ).all()

    print("admin_day", admin_day)
    print("admin_partner", admin_partner)
    print("partner_day", partner_day)
    print("sample", sample)


if __name__ == "__main__":
    main()

