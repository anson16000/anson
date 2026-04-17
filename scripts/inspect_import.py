from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from app.config import load_settings
from app.database import create_session_factory, session_scope
from app.models import FileRegistry, ImportLog
from sqlalchemy import select
settings = load_settings()
_, session_factory = create_session_factory(settings)
with session_scope(session_factory) as session:
    logs = session.scalars(select(ImportLog).order_by(ImportLog.started_at.desc())).all()
    regs = session.scalars(select(FileRegistry).order_by(FileRegistry.imported_at.desc())).all()
    print('LOGS')
    for row in logs[:3]:
        print(row.run_id, row.status, row.total_files, row.processed_files, row.skipped_files, row.error_files, row.message)
    print('REGS')
    for row in regs[:10]:
        print(row.file_type, row.file_name, row.status, row.order_month, row.stage_status, row.error_message)
