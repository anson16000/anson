import csv
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.config import DatabaseConfig, PathsConfig, Settings
from app.database import session_scope
from app.models import DwdOrderDetail
from app.pipeline import ORDER_FIELD_MAP, _canonical_row, _should_skip_success_registry, import_all, init_database
from app.services.import_runtime import build_import_message


class PipelineModesTestCase(unittest.TestCase):
    def test_auto_mode_skips_when_registry_hit(self):
        self.assertTrue(_should_skip_success_registry("auto", True))

    def test_auto_mode_does_not_skip_when_registry_misses(self):
        self.assertFalse(_should_skip_success_registry("auto", False))

    def test_force_mode_never_skips_on_registry_hit(self):
        self.assertFalse(_should_skip_success_registry("force", True))

    def test_order_id_uses_order_number_as_required_primary_key(self):
        row = {
            "订单ID": "52",
            "订单编号": "220202604010828316807014068",
        }

        mapped = _canonical_row(row, ORDER_FIELD_MAP)

        self.assertEqual(mapped["order_id"], "220202604010828316807014068")

    def test_order_id_does_not_fallback_to_order_id_column(self):
        row = {"订单ID": "52"}

        mapped = _canonical_row(row, ORDER_FIELD_MAP)

        self.assertIsNone(mapped["order_id"])

    def test_powerbi_export_failure_does_not_flip_import_to_failed(self):
        status, message = build_import_message(
            status="success",
            mode="auto",
            processed_files=1,
            skipped_files=0,
            touched_months={"2026-03"},
            error_files=0,
            current_message="导入完成；Power BI Parquet 导出失败：目录被占用",
        )

        self.assertEqual(status, "success")
        self.assertIn("Power BI Parquet 导出失败", message)

    def test_same_month_order_files_keep_full_month_and_latest_duplicate_rows(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            orders_raw = root / "orders_raw"
            orders_stage = root / "orders_stage"
            for folder in (
                orders_raw,
                orders_stage,
                root / "orders",
                root / "riders",
                root / "merchants",
                root / "partners",
                root / "logs",
                root / "exports",
                root / "db",
            ):
                folder.mkdir(parents=True, exist_ok=True)

            settings = Settings(
                database=DatabaseConfig(path=(root / "db" / "test.duckdb").as_posix()),
                paths=PathsConfig(
                    orders_raw=orders_raw.as_posix(),
                    orders_stage=orders_stage.as_posix(),
                    orders=(root / "orders").as_posix(),
                    riders=(root / "riders").as_posix(),
                    merchants=(root / "merchants").as_posix(),
                    partners=(root / "partners").as_posix(),
                    logs=(root / "logs").as_posix(),
                    powerbi_parquet=(root / "exports").as_posix(),
                ),
            )

            full_month = orders_raw / "2026.5.1-5.30.csv"
            self._write_order_file(full_month, range(1, 31), partner_name="full-month")
            full_month_time = datetime(2026, 5, 10).timestamp()
            os.utime(full_month, (full_month_time, full_month_time))
            import_all(settings, mode="auto")

            partial_month = orders_raw / "2026.5.1-5.5.csv"
            self._write_order_file(partial_month, range(1, 6), partner_name="newer-partial")
            partial_month_time = datetime(2026, 5, 20).timestamp()
            os.utime(partial_month, (partial_month_time, partial_month_time))
            import_all(settings, mode="auto")

            _, session_factory = init_database(settings)
            with session_scope(session_factory) as session:
                rows = session.query(DwdOrderDetail).order_by(DwdOrderDetail.order_id).all()
                by_id = {row.order_id: row for row in rows}

            self.assertEqual(len(rows), 30)
            self.assertEqual(by_id["ORD-20260501"].partner_name, "newer-partial")
            self.assertEqual(by_id["ORD-20260506"].partner_name, "full-month")

    def _write_order_file(self, path: Path, days, partner_name: str) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "订单编号",
                    "合伙人ID",
                    "合伙人",
                    "商家ID",
                    "商家名称",
                    "用户ID",
                    "配送员ID",
                    "配送员",
                    "订单状态",
                    "添加时间",
                    "支付时间",
                    "接单时间",
                    "完成时间",
                ],
            )
            writer.writeheader()
            for day in days:
                created_at = datetime(2026, 5, day, 10, 0, 0)
                writer.writerow(
                    {
                        "订单编号": f"ORD-202605{day:02d}",
                        "合伙人ID": "628",
                        "合伙人": partner_name,
                        "商家ID": "M001",
                        "商家名称": "测试商家",
                        "用户ID": f"U{day:03d}",
                        "配送员ID": "R001",
                        "配送员": "测试骑手",
                        "订单状态": "已送达",
                        "添加时间": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "支付时间": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "接单时间": (created_at + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S"),
                        "完成时间": (created_at + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )


if __name__ == "__main__":
    unittest.main()
