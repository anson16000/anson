from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from sqlalchemy import select, func
from app.config import load_settings
from app.database import create_session_factory, session_scope
from app.models import OrderDetailRaw
settings = load_settings()
_, session_factory = create_session_factory(settings)
with session_scope(session_factory) as session:
    months = session.execute(select(OrderDetailRaw.order_month, func.count()).group_by(OrderDetailRaw.order_month).order_by(OrderDetailRaw.order_month)).all()
    print(months[:20])
