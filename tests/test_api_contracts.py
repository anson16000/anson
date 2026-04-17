import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException

from app.api import create_app
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

    def test_merchant_threshold_only_exists_on_merchant_like_endpoint(self):
        schema = self.app.openapi()
        merchants_parameters = schema["paths"]["/api/v1/partner/{partner_id}/merchants"]["get"]["parameters"]
        identity_parameters = schema["paths"]["/api/v1/partner/{partner_id}/merchant-like-users"]["get"]["parameters"]

        merchant_param_names = {item["name"] for item in merchants_parameters}
        identity_param_names = {item["name"] for item in identity_parameters}

        self.assertNotIn("merchant_like_threshold", merchant_param_names)
        self.assertIn("merchant_like_threshold", identity_param_names)

    def test_query_window_rejects_over_31_days(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_query_window(date(2026, 3, 1), date(2026, 4, 5))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("31 天", ctx.exception.detail)

    def test_import_parser_supports_auto_and_force_modes(self):
        parser = build_parser()
        args = parser.parse_args(["import", "--mode", "force"])
        self.assertEqual(args.command, "import")
        self.assertEqual(args.mode, "force")


if __name__ == "__main__":
    unittest.main()
