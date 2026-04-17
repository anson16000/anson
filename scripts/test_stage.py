from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from app.utils import detect_largest_sheet, stage_excel_to_csv
source = ROOT / 'data' / 'orders' / '2026年3月订单明细.xls'
stage = ROOT / 'data' / 'orders_stage' / 'stage_test.csv'
print('source_exists', source.exists())
print('sheet', detect_largest_sheet(source))
try:
    result = stage_excel_to_csv(source, stage)
    print('stage_ok', result)
    print('size', result.stat().st_size)
except Exception as exc:
    print(type(exc).__name__, str(exc))
    raise
