from pathlib import Path
import xlrd
path = Path(r"F:\codex\delivery-dashboard\data\orders\2026年3月订单明细.xls")
print(xlrd.inspect_format(path=path.as_posix()))
with path.open('rb') as f:
    print(f.read(16))
