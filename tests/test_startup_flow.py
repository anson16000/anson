import unittest
from pathlib import Path


class StartupFlowTestCase(unittest.TestCase):
    def test_database_source_supports_read_only_duckdb(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "app" / "database.py").read_text(encoding="utf-8")
        self.assertIn('connect_args["read_only"] = True', source)
        self.assertIn("def create_db_engine(settings: Settings, *, read_only: bool = False):", source)

    def test_start_batch_uses_powershell_launcher(self):
        root = Path(__file__).resolve().parents[1]
        batch_source = (root / "02-一键启动看板.bat").read_text(encoding="utf-8")
        self.assertIn("start_dashboard.ps1", batch_source)


if __name__ == "__main__":
    unittest.main()
