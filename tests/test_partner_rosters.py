import unittest

from app.services.partner_rosters import build_partner_riders_payload


class PartnerRostersTestCase(unittest.TestCase):
    def test_build_partner_riders_payload_returns_daily_completed_matrix(self):
        payload = build_partner_riders_payload(
            daily_rows=[
                {
                    "date": "2026-03-01",
                    "rider_id": "R001",
                    "roster_rider_name": "张三",
                    "dwd_rider_name": None,
                    "hire_date": "2026-01-10",
                    "total_orders": 5,
                    "completed_orders": 3,
                    "cancelled_orders": 2,
                    "is_new_rider": 1,
                },
                {
                    "date": "2026-03-02",
                    "rider_id": "R001",
                    "roster_rider_name": "张三",
                    "dwd_rider_name": None,
                    "hire_date": "2026-01-10",
                    "total_orders": 4,
                    "completed_orders": 4,
                    "cancelled_orders": 0,
                    "is_new_rider": 1,
                },
                {
                    "date": "2026-03-02",
                    "rider_id": "R002",
                    "roster_rider_name": None,
                    "dwd_rider_name": "李四",
                    "hire_date": "2026-02-15",
                    "total_orders": 2,
                    "completed_orders": 1,
                    "cancelled_orders": 1,
                    "is_new_rider": 0,
                },
            ],
            tiers=[{"label": "1-9", "min": 1, "max": 9}],
            new_flag="all",
            info={"data_version": "v1", "latest_ready_month": "2026-03"},
            coalesce_text=lambda primary, fallback: primary or fallback or "",
            to_iso_date=lambda value: value,
            target_daily_completed_orders=3,
            target_completed_days=2,
        )

        self.assertEqual(payload["date_columns"], ["2026-03-01", "2026-03-02"])
        self.assertEqual(payload["items"][0]["daily_completed_orders"]["2026-03-01"], 3)
        self.assertEqual(payload["items"][0]["daily_completed_orders"]["2026-03-02"], 4)
        self.assertEqual(payload["items"][1]["completed_orders"], 7)
        self.assertEqual(payload["items"][1]["qualified_days"], 2)
        self.assertEqual(payload["items"][1]["is_target_met"], 1)
        self.assertEqual(payload["items"][1]["daily_completed_orders"]["2026-03-01"], 3)
        self.assertEqual(payload["items"][1]["daily_completed_orders"]["2026-03-02"], 4)
        self.assertEqual(payload["items"][2]["daily_completed_orders"]["2026-03-01"], 0)
        self.assertEqual(payload["items"][2]["daily_completed_orders"]["2026-03-02"], 1)
        self.assertEqual(payload["items"][2]["completed_orders"], 1)
        self.assertEqual(payload["items"][2]["qualified_days"], 0)
        self.assertEqual(payload["items"][2]["is_target_met"], 0)
        self.assertNotIn("total_orders", payload["items"][1])
        self.assertNotIn("cancelled_orders", payload["items"][1])
        self.assertTrue(payload["items"][0]["__pinnedTop"])
        self.assertEqual(payload["items"][0]["completed_orders"], 8)
        self.assertEqual(payload["items"][0]["qualified_days"], 2)
        self.assertEqual(payload["items"][0]["is_target_met"], 1)


if __name__ == "__main__":
    unittest.main()
