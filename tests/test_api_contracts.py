import unittest
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api import _build_hourly_metrics, _calc_partner_recent_daily, create_app
from app.api_support import validate_query_window
from main import build_parser


class ApiContractsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("app.api.init_database", return_value=(None, None)):
            cls.app = create_app()

    def test_page_routes_exist(self):
        paths = {route.path for route in self.app.routes}
        self.assertTrue({"/", "/partner", "/partner/hourly", "/partner/entities", "/alerts", "/direct"}.issubset(paths))

    def test_openapi_contains_partner_entity_endpoints(self):
        schema = self.app.openapi()
        self.assertIn("/api/v1/partner/{partner_id}/merchants", schema["paths"])
        self.assertIn("/api/v1/partner/{partner_id}/merchant-like-users", schema["paths"])
        self.assertIn("/api/v1/partner/{partner_id}/order-sources", schema["paths"])
        self.assertIn("/api/v1/partner/{partner_id}/riders", schema["paths"])
        self.assertIn("/api/v1/admin/partners/fluctuation", schema["paths"])

    def test_merchant_threshold_only_exists_on_merchant_like_endpoint(self):
        schema = self.app.openapi()
        merchants_parameters = schema["paths"]["/api/v1/partner/{partner_id}/merchants"]["get"]["parameters"]
        identity_parameters = schema["paths"]["/api/v1/partner/{partner_id}/merchant-like-users"]["get"]["parameters"]

        merchant_param_names = {item["name"] for item in merchants_parameters}
        identity_param_names = {item["name"] for item in identity_parameters}
        order_source_parameters = schema["paths"]["/api/v1/partner/{partner_id}/order-sources"]["get"]["parameters"]
        order_source_param_names = {item["name"] for item in order_source_parameters}

        self.assertNotIn("merchant_like_threshold", merchant_param_names)
        self.assertIn("merchant_like_threshold", identity_param_names)
        self.assertNotIn("merchant_like_threshold", order_source_param_names)

    def test_riders_endpoint_supports_custom_rider_tiers(self):
        schema = self.app.openapi()
        riders_parameters = schema["paths"]["/api/v1/partner/{partner_id}/riders"]["get"]["parameters"]
        rider_param_names = {item["name"] for item in riders_parameters}
        self.assertIn("rider_tiers", rider_param_names)
        self.assertIn("target_daily_completed_orders", rider_param_names)
        self.assertIn("target_completed_days", rider_param_names)

    def test_fluctuation_endpoint_accepts_region_and_partner_filters(self):
        schema = self.app.openapi()
        fluctuation_parameters = schema["paths"]["/api/v1/admin/partners/fluctuation"]["get"]["parameters"]
        fluctuation_param_names = {item["name"] for item in fluctuation_parameters}

        self.assertTrue({"province", "city", "district", "partner_id"}.issubset(fluctuation_param_names))

    def test_admin_metrics_endpoint_exists(self):
        schema = self.app.openapi()
        self.assertIn("/api/v1/admin/metrics", schema["paths"])

    def test_admin_metrics_ranking_level_supports_all_province_city(self):
        schema = self.app.openapi()
        parameters = schema["paths"]["/api/v1/admin/metrics"]["get"]["parameters"]
        ranking_level = next(item for item in parameters if item["name"] == "ranking_level")
        self.assertEqual(ranking_level["schema"]["type"], "string")
        self.assertEqual(ranking_level["schema"]["default"], "all")

    def test_partner_recent_daily_returns_empty_for_non_all_ranking(self):
        self.assertEqual(_calc_partner_recent_daily(object(), "province"), [])
        self.assertEqual(_calc_partner_recent_daily(object(), "city"), [])

    def test_partner_hourly_metrics_split_rider_type_counts_and_efficiency(self):
        def row(rider_id, employment_type):
            return SimpleNamespace(
                order_date=date(2026, 3, 1),
                order_hour=10,
                accept_time=datetime(2026, 3, 1, 10, 15),
                accept_hour=10,
                rider_id=rider_id,
                is_completed=True,
                is_cancelled=False,
                is_paid=True,
                pay_cancel_minutes=None,
                employment_type=employment_type,
            )

        rows = [
            row("F001", "fulltime"),
            row("P001", "parttime"),
            row("P001", "parttime"),
            row("U001", None),
        ]

        items, hourly_summary = _build_hourly_metrics(rows, threshold=5, include_date=True)

        self.assertEqual(items[0]["accepted_rider_count"], 3)
        self.assertEqual(items[0]["fulltime_accepted_rider_count"], 1)
        self.assertEqual(items[0]["parttime_accepted_rider_count"], 1)
        self.assertEqual(items[0]["fulltime_completed_orders"], 1)
        self.assertEqual(items[0]["parttime_completed_orders"], 2)
        self.assertEqual(items[0]["fulltime_efficiency"], 1.0)
        self.assertEqual(items[0]["parttime_efficiency"], 2.0)
        self.assertEqual(hourly_summary[0]["accepted_rider_count"], 3)
        self.assertGreaterEqual(
            hourly_summary[0]["accepted_rider_count"],
            hourly_summary[0]["fulltime_accepted_rider_count"] + hourly_summary[0]["parttime_accepted_rider_count"],
        )

    def test_partner_hourly_accept_bucket_counts_completed_orders_by_accept_time(self):
        row = SimpleNamespace(
            order_date=date(2026, 4, 6),
            order_hour=23,
            accept_time=datetime(2026, 4, 7, 0, 13, 47),
            accept_hour=0,
            rider_id="13407",
            is_completed=True,
            is_cancelled=False,
            is_paid=True,
            pay_cancel_minutes=None,
            employment_type="parttime",
        )

        items, hourly_summary = _build_hourly_metrics([row], threshold=5, include_date=True, time_bucket="accept")

        self.assertEqual(items[0]["date"], "2026-04-07")
        self.assertEqual(items[0]["hour"], 0)
        self.assertEqual(items[0]["completed_orders"], 1)
        self.assertEqual(items[0]["accepted_rider_count"], 1)
        self.assertEqual(items[0]["parttime_completed_orders"], 1)
        self.assertEqual(items[0]["parttime_accepted_rider_count"], 1)
        self.assertEqual(items[0]["parttime_efficiency"], 1.0)
        self.assertEqual(hourly_summary[0]["completed_orders"], 1)

    def test_partner_hourly_endpoint_supports_accept_time_bucket(self):
        schema = self.app.openapi()
        hourly_parameters = schema["paths"]["/api/v1/partner/{partner_id}/hourly"]["get"]["parameters"]
        hourly_param_names = {item["name"] for item in hourly_parameters}

        self.assertIn("time_bucket", hourly_param_names)

    def test_partner_recent_daily_returns_rows_for_all_ranking(self):
        fake_rows = [
            {
                "partner_id": "P001",
                "partner_name": "测试合伙人",
                "date": date(2026, 3, 1),
                "completed_orders": 12,
            }
        ]

        class FakeResult:
            def mappings(self):
                return fake_rows

        class FakeSession:
            def execute(self, stmt):
                return FakeResult()

        @contextmanager
        def fake_session_scope(_session_factory):
            yield FakeSession()

        with patch("app.api.session_scope", fake_session_scope):
            result = _calc_partner_recent_daily(object(), "all")

        self.assertEqual(
            result,
            [
                {
                    "partner_id": "P001",
                    "partner_name": "测试合伙人",
                    "date": "2026-03-01",
                    "completed_orders": 12,
                }
            ],
        )

    def test_query_window_rejects_over_31_days(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_query_window(date(2026, 3, 1), date(2026, 4, 5))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("31", ctx.exception.detail)

    def test_import_parser_supports_auto_and_force_modes(self):
        parser = build_parser()
        args = parser.parse_args(["import", "--mode", "force"])
        self.assertEqual(args.command, "import")
        self.assertEqual(args.mode, "force")

    def test_main_enables_uvicorn_without_colors(self):
        main_source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        self.assertIn("use_colors=False", main_source)


if __name__ == "__main__":
    unittest.main()
