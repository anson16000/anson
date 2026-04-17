from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    backend: str = "duckdb"
    path: str = "./db/delivery_analysis.duckdb"
    url: str | None = None


class ImportConfig(BaseModel):
    chunk_size: int = 50000
    keep_raw_payload: bool = False
    stage_format: str = "csv"


class PathsConfig(BaseModel):
    orders_raw: str = "./data/orders_raw"
    orders_stage: str = "./data/orders_stage"
    orders: str = "./data/orders"
    riders: str = "./data/riders"
    merchants: str = "./data/merchants"
    partners: str = "./data/partners"
    logs: str = "./logs"
    static: str = "./app/static"


class BusinessConfig(BaseModel):
    valid_order_cancel_threshold_minutes: int = 5
    new_rider_window_days: int = 30
    new_merchant_window_days: int = 30
    new_partner_window_days: int = 90
    merchant_like_user_threshold_orders: int = 20


class AlertConfig(BaseModel):
    large_city_daily_threshold: int = 500
    large_city_change_abs: int = 100
    large_city_change_pct: float = 0.20
    medium_city_daily_threshold: int = 200
    medium_city_change_abs: int = 50
    medium_city_change_pct: float = 0.25
    small_city_change_abs: int = 30
    small_city_change_pct: float = 0.30


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8090
    reload: bool = False


class Settings(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    import_config: ImportConfig = Field(default_factory=ImportConfig, alias="import")
    paths: PathsConfig = Field(default_factory=PathsConfig)
    business: BusinessConfig = Field(default_factory=BusinessConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    model_config = {"populate_by_name": True}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root() / path


def resolve_database_url(settings: Settings) -> str:
    if settings.database.url:
        return settings.database.url

    backend = settings.database.backend.lower().strip()
    db_path = resolve_path(settings.database.path).as_posix()
    if backend == "duckdb":
        return f"duckdb:///{db_path}"
    if backend == "sqlite":
        return f"sqlite:///{db_path}"
    if backend in {"postgres", "postgresql", "mysql"}:
        raise ValueError(f"database.url must be set when backend={backend}")
    raise ValueError(f"Unsupported database backend: {settings.database.backend}")


def ensure_directories(settings: Settings) -> None:
    folders = [
        settings.paths.orders_raw,
        settings.paths.orders_stage,
        settings.paths.orders,
        settings.paths.riders,
        settings.paths.merchants,
        settings.paths.partners,
        settings.paths.logs,
        settings.paths.static,
    ]
    if settings.database.path and settings.database.backend.lower() in {"duckdb", "sqlite"}:
        folders.append(Path(settings.database.path).parent.as_posix())

    for folder in folders:
        resolve_path(str(folder)).mkdir(parents=True, exist_ok=True)


def load_settings(config_path: str | Path = "config/config.yaml") -> Settings:
    path = Path(config_path)
    if not path.is_absolute():
        path = project_root() / path
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    settings = Settings.model_validate(raw)
    ensure_directories(settings)
    return settings
