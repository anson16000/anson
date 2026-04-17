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
    result = conn.execute(select(table).limit(1))
    row = result.first()
    print('keys', list(result.keys())[:10], 'count', len(list(result.keys())))
    print('row_type', type(row))
    print('row_len', len(row) if row is not None else None)
    print('row0_type', type(row[0]) if row is not None and len(row) else None)
    print('row0', row[0] if row is not None and len(row) else None)
