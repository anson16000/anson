from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: inspect_order_workbook.py <path>")

    path = Path(sys.argv[1])
    workbook = pd.ExcelFile(path)
    print({"path": str(path), "sheet_names": workbook.sheet_names})

    for sheet in workbook.sheet_names[:5]:
        frame = pd.read_excel(path, sheet_name=sheet)
        print(
            {
                "sheet": sheet,
                "rows": len(frame),
                "columns": len(frame.columns),
                "headers": [str(col) for col in frame.columns[:20]],
            }
        )


if __name__ == "__main__":
    main()
