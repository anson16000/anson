from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.config import load_settings
from app.database import create_session_factory, session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="检查骑手 ID / 姓名在 stage / ODS / DWD / API 链路中的对应关系")
    parser.add_argument("--rider-id", required=True, help="要检查的骑手ID")
    parser.add_argument("--stage-file", default=None, help="要核对的 stage CSV 文件路径；不传则自动取 orders_stage 下最新的一份 CSV")
    args = parser.parse_args()

    settings = load_settings()
    _, session_factory = create_session_factory(settings)

    rider_id = str(args.rider_id).strip()
    if args.stage_file:
        stage_path = Path(args.stage_file)
    else:
        stage_candidates = sorted((ROOT / "data" / "orders_stage").glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True)
        stage_path = stage_candidates[0] if stage_candidates else ROOT / "data" / "orders_stage" / "MISSING.csv"

    print(f"[RID] {rider_id}")
    print(f"[STAGE] {stage_path}")

    if stage_path.exists():
        import csv

        stage_matches: list[tuple[str, str, str]] = []
        with stage_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if str(row.get("配送员id", "")).strip() == rider_id:
                    stage_matches.append(
                        (
                            str(row.get("订单编号", "")).strip(),
                            str(row.get("配送员id", "")).strip(),
                            str(row.get("配送员", "")).strip(),
                        )
                    )
                if len(stage_matches) >= 5:
                    break
        print("[STAGE MATCHES]")
        for item in stage_matches or [("NONE", "", "")]:
            print(item)
    else:
        print("[STAGE MATCHES]")
        print("STAGE FILE NOT FOUND")

    with session_scope(session_factory) as session:
        ods_rows = session.execute(
            text(
                """
                SELECT order_id, rider_id, rider_name
                FROM ods_order_detail_raw
                WHERE rider_id = :rider_id
                ORDER BY imported_at DESC, row_number DESC
                LIMIT 5
                """
            ),
            {"rider_id": rider_id},
        ).mappings().all()
        dwd_rows = session.execute(
            text(
                """
                SELECT order_id, rider_id, rider_name
                FROM dwd_order_detail
                WHERE rider_id = :rider_id
                ORDER BY create_time DESC NULLS LAST
                LIMIT 5
                """
            ),
            {"rider_id": rider_id},
        ).mappings().all()
        roster_rows = session.execute(
            text(
                """
                SELECT rider_id, rider_name
                FROM rider_roster
                WHERE rider_id = :rider_id
                """
            ),
            {"rider_id": rider_id},
        ).mappings().all()
        order_ids = [str(row["order_id"]) for row in ods_rows if row.get("order_id")]
        dwd_order_rows = []
        ods_order_rows = []
        if order_ids:
            order_id_sql = ", ".join("'" + item.replace("'", "''") + "'" for item in order_ids[:5])
            ods_order_rows = session.execute(
                text(
                    f"""
                    SELECT order_id, user_id, rider_id, rider_name, merchant_id, merchant_name, shop_name
                    FROM ods_order_detail_raw
                    WHERE order_id IN ({order_id_sql})
                    ORDER BY imported_at DESC, row_number DESC
                    LIMIT 5
                    """
                )
            ).mappings().all()
            dwd_order_rows = session.execute(
                text(
                    f"""
                    SELECT order_id, user_id, rider_id, rider_name, merchant_id, merchant_name, shop_name
                    FROM dwd_order_detail
                    WHERE order_id IN ({order_id_sql})
                    ORDER BY create_time DESC NULLS LAST
                    LIMIT 5
                    """
                )
            ).mappings().all()

    print("[ODS MATCHES]")
    for row in ods_rows or [{"order_id": "NONE", "rider_id": "", "rider_name": ""}]:
        print(dict(row))

    print("[DWD MATCHES]")
    for row in dwd_rows or [{"order_id": "NONE", "rider_id": "", "rider_name": ""}]:
        print(dict(row))

    print("[ROSTER MATCHES]")
    for row in roster_rows or [{"rider_id": "NONE", "rider_name": ""}]:
        print(dict(row))

    print("[DWD BY ODS ORDER_ID]")
    for row in dwd_order_rows or [{"order_id": "NONE", "user_id": "", "rider_id": "", "rider_name": "", "merchant_id": "", "merchant_name": "", "shop_name": ""}]:
        print(dict(row))

    print("[ODS BY ORDER_ID]")
    for row in ods_order_rows or [{"order_id": "NONE", "user_id": "", "rider_id": "", "rider_name": "", "merchant_id": "", "merchant_name": "", "shop_name": ""}]:
        print(dict(row))


if __name__ == "__main__":
    main()
