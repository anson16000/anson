import unittest

from app.config import PathsConfig
from app.powerbi_export import EXCLUDED_PARTNER_IDS, POWERBI_EXPORTS, _copy_query_to_parquet_sql
from main import build_parser


class PowerBiExportTestCase(unittest.TestCase):
    def test_powerbi_export_manifest_contains_required_chinese_files(self):
        required_files = {
            "日期维度.parquet",
            "合伙人维度.parquet",
            "骑手维度.parquet",
            "商家维度.parquet",
            "全国日汇总.parquet",
            "合伙人日汇总.parquet",
            "小时运力汇总.parquet",
            "骑手日汇总.parquet",
            "商家日汇总.parquet",
            "订单明细事实表.parquet",
            "订单来源汇总.parquet",
            "用户商家识别汇总.parquet",
            "合伙人健康度.parquet",
            "合伙人波动预警.parquet",
            "合伙人风险建议.parquet",
            "数据版本.parquet",
        }

        self.assertTrue(required_files.issubset(set(POWERBI_EXPORTS)))

    def test_default_powerbi_parquet_path(self):
        self.assertEqual(PathsConfig().powerbi_parquet, "./exports/powerbi_parquet")

    def test_export_powerbi_command_exists(self):
        parser = build_parser()
        args = parser.parse_args(["export-powerbi"])

        self.assertEqual(args.command, "export-powerbi")

    def test_partner_day_export_contains_chinese_revenue_fields(self):
        query = POWERBI_EXPORTS["合伙人日汇总.parquet"]

        self.assertIn('"合伙人收入总额"', query)
        self.assertIn('"合伙人补贴"', query)
        self.assertIn('"经营利润"', query)
        self.assertIn('"骑手提成总额"', query)
        self.assertIn('"客单价"', query)
        self.assertIn('"人效"', query)

    def test_order_fact_export_contains_linking_keys_and_numeric_flags(self):
        query = POWERBI_EXPORTS["订单明细事实表.parquet"]

        self.assertIn('order_id AS "订单编号"', query)
        self.assertIn('partner_id AS "合伙人ID"', query)
        self.assertIn('merchant_id AS "商家ID"', query)
        self.assertIn('rider_id AS "骑手ID"', query)
        self.assertIn('"订单来源"', query)
        self.assertIn('CASE WHEN is_completed THEN 1 ELSE 0 END AS "完成订单数"', query)
        self.assertIn('CASE WHEN is_valid_order THEN 1 ELSE 0 END AS "有效订单数"', query)
        self.assertIn('ROUND(hq_income, 2) AS "总部收入"', query)
        self.assertIn('ROUND(maiyatian_income, 2) AS "麦芽田收入"', query)
        self.assertIn('ROUND(insurance_fee, 2) AS "保险费"', query)
        self.assertIn('ROUND(hq_income - maiyatian_income, 2) AS "系统佣金收入"', query)

    def test_powerbi_exports_exclude_test_partner_101(self):
        self.assertIn("101", EXCLUDED_PARTNER_IDS)

        for file_name, query in POWERBI_EXPORTS.items():
            if file_name in {"日期维度.parquet", "骑手维度.parquet", "商家维度.parquet", "数据版本.parquet"}:
                continue
            self.assertIn("101", query, msg=file_name)
            self.assertIn("NOT IN", query, msg=file_name)

    def test_powerbi_exports_use_snappy_parquet(self):
        sql = _copy_query_to_parquet_sql("SELECT 1 AS value", PathsConfig().powerbi_parquet)

        self.assertIn("FORMAT PARQUET", sql)
        self.assertIn("COMPRESSION SNAPPY", sql)


if __name__ == "__main__":
    unittest.main()
