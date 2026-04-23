import unittest

from app.pipeline import ORDER_FIELD_MAP, _canonical_row, _should_skip_success_registry


class PipelineModesTestCase(unittest.TestCase):
    def test_auto_mode_skips_when_registry_hit(self):
        self.assertTrue(_should_skip_success_registry("auto", True))

    def test_auto_mode_does_not_skip_when_registry_misses(self):
        self.assertFalse(_should_skip_success_registry("auto", False))

    def test_force_mode_never_skips_on_registry_hit(self):
        self.assertFalse(_should_skip_success_registry("force", True))

    def test_order_id_prefers_order_number_over_order_id(self):
        row = {
            "订单ID": "52",
            "订单编号": "220202604010828316807014068",
        }

        mapped = _canonical_row(row, ORDER_FIELD_MAP)

        self.assertEqual(mapped["order_id"], "220202604010828316807014068")


if __name__ == "__main__":
    unittest.main()
