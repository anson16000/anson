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
        self.assertIn('id="adminProvinceControl"', html)
        self.assertIn('id="adminCityControl"', html)
        self.assertIn('id="adminDistrictControl"', html)
        self.assertIn('id="adminPartnerControl"', html)

    def test_alerts_page_contains_shortcuts_and_partner_filters(self):
        content = (ROOT / "app" / "static" / "alerts.js").read_text(encoding="utf-8")
        html = (ROOT / "app" / "static" / "alerts.html").read_text(encoding="utf-8")

        self.assertIn('addDateShortcuts("#alertsStartDate", "#alertsEndDate"', content)
        self.assertIn('id="alertsProvinceControl"', html)
        self.assertIn('id="alertsCityControl"', html)
        self.assertIn('id="alertsDistrictControl"', html)
        self.assertIn('id="alertsPartnerControl"', html)

    def test_partner_summary_contains_actual_received_and_avg_ticket_price(self):
        content = (ROOT / "app" / "static" / "modules" / "partner-sections.js").read_text(encoding="utf-8")

        self.assertIn("summary.actual_received_total", content)
        self.assertIn("summary.avg_ticket_price", content)

    def test_entities_page_uses_daily_rider_columns_and_tier_ui(self):
        html = (ROOT / "app" / "static" / "entities.html").read_text(encoding="utf-8")
        js = (ROOT / "app" / "static" / "entities.js").read_text(encoding="utf-8")
        sections = (ROOT / "app" / "static" / "modules" / "entities-sections.js").read_text(encoding="utf-8")

        self.assertIn('id="entitiesRiderTierInput"', html)
        self.assertIn('id="entitiesRiderTierTable"', html)
        self.assertIn('id="entitiesRiderRosterTable"', html)
        self.assertIn('id="entitiesRiderTargetCompleted"', html)
        self.assertIn('id="entitiesRiderTargetDays"', html)
        self.assertIn("parseTierText", js)
        self.assertIn("renderRiderRoster(riders.items || [], riders.date_columns || [])", js)
        self.assertIn("renderRiderTierTable", js)
        self.assertIn("target_daily_completed_orders: riderTargetCompletedOrders()", js)
        self.assertIn("target_completed_days: riderTargetCompletedDays()", js)
        self.assertIn("function formatMonthDay", sections)
        self.assertIn('label: "序号"', sections)
        self.assertIn('label: "完成总订单"', sections)
        self.assertIn('label: "是否达标"', sections)


if __name__ == "__main__":
    unittest.main()
