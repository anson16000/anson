from pathlib import Path
import sys
from sqlalchemy import create_engine

ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from app.database import Base
from app import models  # noqa
from app.config import load_settings, resolve_database_url

settings = load_settings()
db_path = ROOT / "db" / "duckdb_compat_test.duckdb"
if db_path.exists():
    db_path.unlink()
settings.database.backend = 'duckdb'
settings.database.path = './db/duckdb_compat_test.duckdb'
engine = create_engine(resolve_database_url(settings), future=True)
Base.metadata.create_all(engine)
print('OK')
