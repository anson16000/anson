from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings
def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "app.api:create_app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        factory=True,
        use_colors=False,
    )


if __name__ == "__main__":
    main()
