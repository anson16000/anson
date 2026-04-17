from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.api import create_app


def main() -> None:
    app = create_app()
    client = TestClient(app)
    for path in ("/api/v1/meta", "/api/v1/admin/metrics"):
        try:
            response = client.get(path)
            print({"path": path, "status_code": response.status_code})
            print(response.text[:1000])
        except Exception:
            print({"path": path, "status_code": "exception"})
            traceback.print_exc()


if __name__ == "__main__":
    main()
