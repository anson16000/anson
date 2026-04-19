from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_settings
from app.database import session_scope
from app.pipeline import _all_order_months, init_database, rebuild_ads, rebuild_dwd, rebuild_standard_tables
from app.services.import_runtime import publish_data_version


def main() -> None:
    settings = load_settings()
    _, session_factory = init_database(settings)
    run_id = uuid4().hex

    with session_scope(session_factory) as session:
        session = session  # type: Session
        months = _all_order_months(session)
        if not months:
            raise RuntimeError("未找到可重建的订单月份。")

        print(f"rebuild_months={sorted(months)}")
        rebuild_standard_tables(session)
        rebuild_dwd(session, settings, months, run_id)
        rebuild_ads(session, months, run_id)
        data_version, latest_ready_month = publish_data_version(session, run_id)
        print(f"data_version={data_version}")
        print(f"latest_ready_month={latest_ready_month}")


if __name__ == "__main__":
    main()
