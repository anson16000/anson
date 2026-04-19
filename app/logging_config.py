from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: str = "./logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(log_dir) / "app.log", encoding="utf-8"),
        ],
    )
