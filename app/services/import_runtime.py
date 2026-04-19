from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdsPartnerDayMetrics, DataPublishVersion, EtlJobRun, EtlStageMetrics, FileRegistry, ImportLog


def should_skip_success_registry(mode: str, registry_hit: bool) -> bool:
    return mode != "force" and registry_hit


def publish_data_version(session: Session, run_id: str) -> tuple[str, str | None]:
    latest_ready_month = session.scalar(select(func.max(AdsPartnerDayMetrics.order_month)))
    data_version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{run_id[:8]}"
    session.add(
        DataPublishVersion(
            data_version=data_version,
            run_id=run_id,
            latest_ready_month=latest_ready_month,
            published_at=datetime.utcnow(),
            status="ready",
        )
    )
    return data_version, latest_ready_month


def build_import_message(
    *,
    status: str,
    mode: str,
    processed_files: int,
    skipped_files: int,
    touched_months: set[str],
    error_files: int,
) -> tuple[str, str]:
    final_status = status
    message = "导入完成"
    if final_status == "success" and error_files > 0:
        final_status = "partial_success"
        message = "部分文件处理失败，请查看导入状态。"
    elif final_status == "success":
        if mode == "force":
            message = (
                "导入完成：已强制重建当前文件对应月份"
                if processed_files > 0 or touched_months
                else "导入完成：已执行强制重建，但当前没有可处理的数据变更"
            )
        elif processed_files == 0 and skipped_files > 0:
            message = "导入完成：文件未变化，已跳过已成功导入的文件"
        else:
            message = "导入完成"
    return final_status, message


def get_latest_import_info(session: Session) -> dict[str, Any]:
    last_log = session.scalar(select(ImportLog).order_by(ImportLog.started_at.desc()))
    last_job = session.scalar(select(EtlJobRun).order_by(EtlJobRun.started_at.desc()))
    latest_publish = session.scalar(select(DataPublishVersion).order_by(DataPublishVersion.published_at.desc()))
    latest_date = session.scalar(select(func.max(AdsPartnerDayMetrics.date)))

    versions: dict[str, str] = {}
    for file_type in ("riders", "merchants", "partners"):
        latest = session.scalar(
            select(FileRegistry.imported_at)
            .where(FileRegistry.file_type == file_type, FileRegistry.status == "success")
            .order_by(FileRegistry.imported_at.desc())
        )
        if latest:
            versions[file_type] = latest.isoformat()

    stage_seconds: dict[str, float] = {}
    if last_job:
        rows = session.scalars(
            select(EtlStageMetrics).where(EtlStageMetrics.run_id == last_job.run_id).order_by(EtlStageMetrics.started_at)
        ).all()
        for row in rows:
            stage_seconds[row.stage_name] = round(row.duration_seconds or 0.0, 3)

    return {
        "last_import_time": last_log.ended_at.isoformat() if last_log and last_log.ended_at else None,
        "last_import_status": last_log.status if last_log else "never_run",
        "latest_data_date": latest_date.isoformat() if latest_date else None,
        "roster_versions": versions,
        "data_version": latest_publish.data_version if latest_publish else None,
        "latest_ready_month": latest_publish.latest_ready_month if latest_publish else None,
        "latest_run_id": last_job.run_id if last_job else None,
        "total_seconds": round(last_job.total_seconds or 0.0, 3) if last_job else 0.0,
        "stage_seconds": stage_seconds,
    }
