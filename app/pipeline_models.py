from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PreparedOrderFile:
    file_id: str
    file_path: Path
    file_name: str
    file_size: int
    sha256: str
    source_type: str
    stage_file_path: Path
    stage_status: str
    inferred_month: str | None
    staged_rows: int = 0
    order_months: set[str] = field(default_factory=set)


@dataclass
class PreparedRosterFile:
    file_id: str
    file_type: str
    file_path: Path
    file_name: str
    file_size: int
    sha256: str


@dataclass
class PreprocessOutcome:
    order_files: list[PreparedOrderFile]
    roster_files: list[PreparedRosterFile]
    skipped_files: int
    error_files: int
    input_rows: int
    output_rows: int


@dataclass
class LoadStageOutcome:
    success_files: list[PreparedOrderFile]
    error_files: int
    input_rows: int
    output_rows: int


@dataclass
class MergeOutcome:
    touched_months: set[str]
    roster_changed: bool
    processed_files: int
    error_files: int
    input_rows: int
    output_rows: int


@dataclass
class ImportResult:
    mode: str
    run_id: str
    total_files: int
    processed_files: int
    skipped_files: int
    error_files: int
    status: str
    message: str
    affected_months: list[str]
    data_version: str | None
    latest_ready_month: str | None
    preprocess_seconds: float
    load_stage_seconds: float
    merge_ods_seconds: float
    build_ads_seconds: float
    publish_seconds: float
    total_seconds: float
