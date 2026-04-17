from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def inspect_file(path: Path, label: str) -> None:
    print(f"\n== {label} ==")
    print(f"path={path}")
    workbook = pd.read_excel(path, sheet_name=None, dtype=str)
    print(f"sheets={list(workbook.keys())}")
    if not workbook:
        return
    frame = max(workbook.values(), key=lambda item: (len(item.index), len(item.columns)))
    print("columns=", list(frame.columns))
    preview = frame.head(10).fillna("")
    print(preview.to_string(index=False))


def main() -> None:
    root = Path(r"F:\codex\delivery-dashboard\data")
    inspect_file(root / "riders" / "帮手信息.xlsx", "riders")
    inspect_file(root / "merchants" / "商户信息.xlsx", "merchants")


if __name__ == "__main__":
    main()
