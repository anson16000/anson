from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from sqlalchemy import select, func
from app.config import load_settings
from app.database import create_session_factory, session_scope
from app.models import OrderDetailRaw, DwdOrderDetail, AdsPartnerDayMetrics, AdsPartnerHourMetrics, AdsAdminDayMetrics
settings = load_settings()
_, session_factory = create_session_factory(settings)
with session_scope(session_factory) as session:
    print('raw', session.scalar(select(func.count()).select_from(OrderDetailRaw)))
    print('dwd', session.scalar(select(func.count()).select_from(DwdOrderDetail)))
    print('partner_day', session.scalar(select(func.count()).select_from(AdsPartnerDayMetrics)))
    print('partner_hour', session.scalar(select(func.count()).select_from(AdsPartnerHourMetrics)))
    print('admin_day', session.scalar(select(func.count()).select_from(AdsAdminDayMetrics)))
    months = session.execute(select(DwdOrderDetail.order_month, func.count()).group_by(DwdOrderDetail.order_month).order_by(DwdOrderDetail.order_month)).all()
    print('months', months)
