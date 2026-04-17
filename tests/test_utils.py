import unittest
from pathlib import Path

from app.utils import (
    infer_order_month_from_filename,
    infer_order_month_from_value,
    normalize_headers,
    normalize_identifier,
    parse_float,
    parse_region,
    safe_stage_name,
)


class UtilsTestCase(unittest.TestCase):
    def test_normalize_identifier_handles_numeric_and_fullwidth_values(self):
        self.assertEqual(normalize_identifier(123.0), "123")
        self.assertEqual(normalize_identifier("00123"), "123")
        self.assertEqual(normalize_identifier("+45.00"), "45")
        self.assertIsNone(normalize_identifier("-"))

    def test_parse_float_strips_currency_and_text(self):
        self.assertEqual(parse_float("¥1,234.50"), 1234.5)
        self.assertEqual(parse_float("约-88元"), -88.0)
        self.assertEqual(parse_float(None), 0.0)
        self.assertEqual(parse_float("无效值"), 0.0)

    def test_normalize_headers_deduplicates_names(self):
        self.assertEqual(
            normalize_headers([" 合伙人名称 ", "合伙人名称", "订单（实收）", None]),
            ["合伙人名称", "合伙人名称.1", "订单(实收)", "column"],
        )

    def test_safe_stage_name_keeps_meaningful_stem(self):
        result = safe_stage_name(Path("2026年3月 订单明细.xlsx"), "abcdef1234567890", "csv")
        self.assertEqual(result, "2026年3月_订单明细__abcdef123456.csv")

    def test_safe_stage_name_handles_nonexistent_path_gracefully(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            safe_stage_name(Path("nonexistent_file.xlsx"), "abc123", "csv")
        self.assertIn("nonexistent_file.xlsx", str(ctx.exception))

    def test_parse_region_supports_direct_city_and_split_values(self):
        self.assertEqual(parse_region("北京市 朝阳区"), ("北京市", "北京市", "朝阳区"))
        self.assertEqual(parse_region("广东省 / 深圳市 / 南山区"), ("广东省", "深圳市", "南山区"))
        self.assertEqual(parse_region(None), (None, None, None))

    def test_infer_order_month_from_inputs(self):
        self.assertEqual(infer_order_month_from_filename("2026年3月订单明细.xls"), "2026-03")
        self.assertEqual(infer_order_month_from_filename("orders_2026-11.csv"), "2026-11")
        self.assertIsNone(infer_order_month_from_filename("orders.csv"))
        self.assertEqual(infer_order_month_from_value("2026-04-15 08:30:00"), "2026-04")
        self.assertIsNone(infer_order_month_from_value("not-a-date"))


if __name__ == "__main__":
    unittest.main()
