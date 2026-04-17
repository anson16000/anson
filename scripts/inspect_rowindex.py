from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from sqlalchemy import select
from app.config import load_settings
from app.database import create_session_factory, session_scope
from app.models import OrderDetailRaw
settings = load_settings()
_, session_factory = create_session_factory(settings)
with session_scope(session_factory) as session:
    conn = session.connection()
    table = OrderDetailRaw.__table__
    row = conn.execute(select(table).limit(1)).first()
    print('order_id', row[6])
