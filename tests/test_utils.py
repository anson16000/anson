import unittest
from pathlib import Path

from app.utils import (
    infer_order_month_from_filename,
    infer_order_month_from_value,
    normalize_headers,
    normalize_identifier,
    parse_float,
    safe_stage_name,
)


class UtilsTestCase(unittest.TestCase):
    def test_normalize_identifier_handles_numeric_values(self):
        self.assertEqual(normalize_identifier(123.0), "123")
        self.assertEqual(normalize_identifier("00123"), "123")
        self.assertEqual(normalize_identifier("+45.00"), "45")
        self.assertIsNone(normalize_identifier("-"))

    def test_parse_float_strips_currency_and_text(self):
        self.assertEqual(parse_float("￥1,234.50"), 1234.5)
        self.assertEqual(parse_float("净额-88元"), -88.0)
        self.assertEqual(parse_float(None), 0.0)
        self.assertEqual(parse_float("无效值"), 0.0)

    def test_normalize_headers_deduplicates_names(self):
        self.assertEqual(
            normalize_headers([" Partner Name ", "Partner Name", "Order(Actual)", None]),
            ["partnername", "partnername.1", "order(actual)", "column"],
        )

    def test_safe_stage_name_keeps_meaningful_stem(self):
        result = safe_stage_name(Path("2026-03 orders.xlsx"), "abcdef1234567890", "csv")
        self.assertEqual(result, "2026-03_orders__abcdef123456.csv")

    def test_infer_order_month_from_inputs(self):
        self.assertEqual(infer_order_month_from_filename("2026年3月订单明细.xls"), "2026-03")
        self.assertEqual(infer_order_month_from_filename("orders_2026-11.csv"), "2026-11")
        self.assertIsNone(infer_order_month_from_filename("orders.csv"))
        self.assertEqual(infer_order_month_from_value("2026-04-15 08:30:00"), "2026-04")
        self.assertIsNone(infer_order_month_from_value("not-a-date"))


if __name__ == "__main__":
    unittest.main()
