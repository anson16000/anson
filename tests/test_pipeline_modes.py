import unittest

from app.pipeline import _should_skip_success_registry


class PipelineModesTestCase(unittest.TestCase):
    def test_auto_mode_skips_when_registry_hit(self):
        self.assertTrue(_should_skip_success_registry("auto", True))

    def test_auto_mode_does_not_skip_when_registry_misses(self):
        self.assertFalse(_should_skip_success_registry("auto", False))

    def test_force_mode_never_skips_on_registry_hit(self):
        self.assertFalse(_should_skip_success_registry("force", True))


if __name__ == "__main__":
    unittest.main()
