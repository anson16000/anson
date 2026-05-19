import unittest

from app.pipeline import ORDER_FIELD_MAP, _canonical_row, _should_skip_success_registry
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


if __name__ == "__main__":
    unittest.main()
