import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticPageContentTestCase(unittest.TestCase):
    def test_admin_page_contains_date_shortcuts_and_filters(self):
        content = (ROOT / "app" / "static" / "admin.js").read_text(encoding="utf-8")
        html = (ROOT / "app" / "static" / "admin.html").read_text(encoding="utf-8")
        date_js = (ROOT / "app" / "static" / "core" / "date.js").read_text(encoding="utf-8")

        self.assertIn('addDateShortcuts("#adminStartDate", "#adminEndDate"', content)
        self.assertIn("今天", date_js)
        self.assertIn("昨天", date_js)
        self.assertIn("近7天", date_js)
        self.assertIn("近30天", date_js)
        self.assertIn("id=\"adminProvinceControl\"", html)
        self.assertIn("id=\"adminCityControl\"", html)
        self.assertIn("id=\"adminDistrictControl\"", html)
        self.assertIn("id=\"adminPartnerControl\"", html)

    def test_alerts_page_contains_shortcuts_and_partner_filters(self):
        content = (ROOT / "app" / "static" / "alerts.js").read_text(encoding="utf-8")
        html = (ROOT / "app" / "static" / "alerts.html").read_text(encoding="utf-8")

        self.assertIn('addDateShortcuts("#alertsStartDate", "#alertsEndDate"', content)
        self.assertIn("id=\"alertsProvinceControl\"", html)
        self.assertIn("id=\"alertsCityControl\"", html)
        self.assertIn("id=\"alertsDistrictControl\"", html)
        self.assertIn("id=\"alertsPartnerControl\"", html)


if __name__ == "__main__":
    unittest.main()
