import unittest
from types import SimpleNamespace

from app.services.partner_metrics import build_partner_overview_payload


class PartnerMetricsTestCase(unittest.TestCase):
    def test_overview_uses_runtime_valid_order_counts_when_threshold_changes(self):
        latest_row = SimpleNamespace(
            partner_name="测试合伙人",
            province="广东省",
            city="广州市",
            district="天河区",
        )
        dwd_rows = [
            SimpleNamespace(
                is_completed=True,
                is_cancelled=False,
                is_paid=True,
                pay_cancel_minutes=0,
                is_new_rider_order=True,
                is_new_merchant_order=False,
                accept_time=10,
                complete_time=35,
            ),
            SimpleNamespace(
                is_completed=False,
                is_cancelled=True,
                is_paid=True,
                pay_cancel_minutes=6,
                is_new_rider_order=False,
                is_new_merchant_order=False,
                accept_time=None,
                complete_time=None,
            ),
        ]
        payload = build_partner_overview_payload(
            info={"data_version": "v1", "latest_ready_month": "2026-03"},
            partner_id="P001",
            latest_row=latest_row,
            rows=[],
            dwd_rows=dwd_rows,
            summary={
                "total_orders": 99,
                "valid_orders": 99,
                "completed_orders": 99,
                "cancelled_orders": 99,
                "hq_subsidy_total": 0.0,
                "partner_subsidy_total": 0.0,
                "new_rider_orders": 0,
                "new_merchant_orders": 0,
            },
            active_riders=1,
            active_merchants=1,
            new_riders=1,
            new_merchants=0,
            amount_row={
                "completed_amount_paid": 12.5,
                "rider_income_total": 3.0,
                "partner_income_total": 5.0,
                "partner_subsidy_total": 1.0,
                "valid_cancel_orders": 1,
            },
            threshold=5,
            sla_minutes=40,
            active_completed_threshold=1,
            day_count=1,
            calc_duration_minutes=lambda accept_time, complete_time: complete_time - accept_time if accept_time is not None and complete_time is not None else None,
            safe_ratio=lambda numerator, denominator: numerator / denominator if denominator else 0.0,
            calc_efficiency=lambda completed_orders, active_riders: completed_orders / active_riders if active_riders else 0.0,
            build_order_summary=lambda total_orders, valid_orders, completed_orders, cancelled_orders, **extra: {
                "total_orders": int(total_orders),
                "valid_orders": int(valid_orders),
                "valid_completed_orders": int(completed_orders),
                "valid_completion_rate": completed_orders / valid_orders if valid_orders else 0.0,
                "completed_orders": int(completed_orders),
                "cancelled_orders": int(cancelled_orders),
                "completion_rate": completed_orders / total_orders if total_orders else 0.0,
                "cancel_rate": cancelled_orders / total_orders if total_orders else 0.0,
                **extra,
            },
            build_health_score=lambda metrics, day_count: {"score": metrics["valid_orders"], "day_count": day_count},
        )

        self.assertEqual(payload["summary"]["total_orders"], 2)
        self.assertEqual(payload["summary"]["valid_orders"], 2)
        self.assertEqual(payload["summary"]["completed_orders"], 1)
        self.assertEqual(payload["summary"]["cancelled_orders"], 1)
        self.assertEqual(payload["summary"]["valid_completed_orders"], 1)


if __name__ == "__main__":
    unittest.main()
