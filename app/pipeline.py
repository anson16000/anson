from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.config import Settings, resolve_path
from app.database import Base, create_session_factory, session_scope
from app.models import (
    AbnormalOrder,
    AdsAdminDayMetrics,
    AdsAdminPartnerMetrics,
    AdsDirectCancelDayMetrics,
    AdsDirectCouponMetrics,
    AdsDirectHourMetrics,
    AdsDirectMerchantDayMetrics,
    AdsDirectNewMerchantMetrics,
    AdsDirectNewRiderMetrics,
    AdsDirectOrderSourceDayMetrics,
    AdsPartnerDayMetrics,
    AdsPartnerHourMetrics,
    AdsPartnerMerchantDayMetrics,
    AdsPartnerRiderDayMetrics,
    AdsPartnerUserMerchantMetrics,
    DwdOrderDetail,
    EtlJobRun,
    EtlStageMetrics,
    FileRegistry,
    ImportLog,
    MerchantRoster,
    MerchantRosterRaw,
    OrderDetailRaw,
    PartnerRoster,
    PartnerRosterRaw,
    RiderRoster,
    RiderRosterRaw,
)
from app.pipeline_models import ImportResult, LoadStageOutcome, MergeOutcome, PreparedOrderFile, PreparedRosterFile, PreprocessOutcome
from app.services.import_runtime import (
    build_import_message,
    get_latest_import_info as _get_latest_import_info,
    publish_data_version,
    should_skip_success_registry,
)
from app.utils import (
    clean_text,
    dump_json,
    file_sha256,
    infer_order_month_from_filename,
    load_table,
    normalize_identifier,
    normalize_header,
    parse_date,
    parse_region,
    safe_stage_name,
    stage_csv_to_csv,
    stage_excel_to_csv,
)


ORDER_FIELD_MAP = {
    "order_id": ["订单id", "订单ID", "订单编号", "订单号", "order_id"],
    "partner_id": ["合伙人id", "合伙人ID", "合伙人编号", "partner_id"],
    "partner_name": ["合伙人", "合伙人名称", "合伙人公司名", "合伙人公司名称", "partner_name"],
    "merchant_id": ["商家id", "商家ID", "商户id", "商户ID", "merchant_id"],
    "merchant_name": ["商家", "商家名称", "商户名称", "merchant_name"],
    "shop_name": [],
    "user_id": ["用户id", "用户ID", "下单用户id", "下单用户ID", "user_id"],
    "rider_id": ["配送员id", "配送员ID", "帮手id", "帮手ID", "骑手id", "骑手ID", "rider_id"],
    "rider_name": ["配送员", "配送员名称", "帮手姓名", "骑手姓名", "rider_name"],
    "employment_status": ["在职状态", "employment_status"],
    "order_status": ["订单状态", "状态", "order_status"],
    "customer_service_id": ["客服编号", "customer_service_id"],
    "order_source": ["下单来源", "渠道来源", "order_source"],
    "added_at": ["添加时间", "下单时间", "创建时间", "create_time", "added_at"],
    "pay_time": ["支付时间", "pay_time"],
    "accept_time": ["接单时间", "accept_time"],
    "cancel_time": ["取消时间", "cancel_time"],
    "complete_time": ["完成时间", "送达时间", "complete_time"],
    "order_price": ["订单价格", "订单金额", "order_price"],
    "amount_payable": ["应付金额", "amount_payable"],
    "amount_paid": ["实付金额", "amount_paid"],
    "hq_discount_amount": ["总部优惠金额", "总部优惠", "hq_discount_amount"],
    "discount_amount": ["优惠金额", "discount_amount"],
    "coupon_id": ["优惠券id", "优惠券ID", "优惠劵id", "优惠劵ID", "coupon_id"],
    "marketing_coupon_id": ["营销优惠券id", "营销优惠券ID", "营销优惠劵id", "营销优惠劵ID", "marketing_coupon_id"],
    "rider_income": ["帮手收入", "骑手收入", "rider_income"],
    "partner_income": ["合伙人收入", "partner_income"],
}

RIDER_FIELD_MAP = {
    "rider_id": ["帮手id", "帮手ID", "配送员id", "配送员ID", "骑手id", "骑手ID", "rider_id"],
    "rider_name": ["帮手姓名", "配送员", "配送员名称", "骑手姓名", "rider_name"],
    "hire_date": ["入职时间", "入职日期", "hire_date"],
    "status": ["状态", "status"],
    "partner_name": ["所属合伙人", "partner_name"],
    "region": ["所属区域", "区域", "region"],
}

MERCHANT_FIELD_MAP = {
    "merchant_id": ["商家id", "商家ID", "商户id", "商户ID", "merchant_id"],
    "merchant_name": ["商家", "商家名称", "商户名称", "merchant_name"],
    "partner_name": ["所属合伙人", "partner_name"],
    "region": ["所属区域", "区域", "region"],
    "register_date": ["注册时间", "注册日期", "register_date"],
    "status": ["状态", "status"],
}

PARTNER_FIELD_MAP = {
    "partner_id": ["id", "ID", "合伙人id", "合伙人ID", "partner_id"],
    "partner_name": ["合伙人", "合伙人名称", "合伙人公司名", "合伙人公司名称", "partner_name"],
    "open_date": ["成立时间", "开城时间", "open_date"],
    "region_raw": ["合伙人区域", "区域", "region_raw"],
    "status": ["状态", "status"],
}

MONTH_PATTERN = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
IDENTIFIER_FIELDS = {"order_id", "partner_id", "merchant_id", "user_id", "rider_id"}


def init_database(settings: Settings):
    engine, session_factory = create_session_factory(settings)
    Base.metadata.create_all(engine)
    _migrate_tables(engine)
    return engine, session_factory


def _migrate_tables(engine) -> None:
    table_columns = {
        "ods_order_detail_raw": [
            ("rider_name", "VARCHAR"),
            ("employment_status", "VARCHAR"),
            ("customer_service_id", "VARCHAR"),
            ("order_source", "VARCHAR"),
            ("accept_time", "VARCHAR"),
            ("shop_name", "VARCHAR"),
            ("order_price", "VARCHAR"),
            ("amount_payable", "VARCHAR"),
            ("coupon_id", "VARCHAR"),
            ("amount_paid", "VARCHAR"),
            ("rider_income", "VARCHAR"),
            ("partner_income", "VARCHAR"),
        ],
        "dwd_order_detail": [
            ("shop_name", "VARCHAR"),
            ("employment_status", "VARCHAR"),
            ("employment_type", "VARCHAR"),
            ("customer_service_id", "VARCHAR"),
            ("order_source", "VARCHAR"),
            ("accept_time", "TIMESTAMP"),
            ("accept_hour", "INTEGER"),
            ("order_elapsed_minutes_to_cancel", "DOUBLE"),
            ("is_valid_cancel_order", "BOOLEAN"),
            ("service_online_flag", "BOOLEAN"),
            ("is_timeout_cancel", "BOOLEAN"),
            ("is_not_timeout_cancel", "BOOLEAN"),
            ("is_unaccepted_cancel", "BOOLEAN"),
            ("is_accepted_cancel", "BOOLEAN"),
            ("is_rider_noliability_cancel", "BOOLEAN"),
            ("has_coupon_order", "BOOLEAN"),
            ("order_price", "DOUBLE"),
            ("amount_payable", "DOUBLE"),
            ("amount_paid", "DOUBLE"),
            ("rider_income", "DOUBLE"),
            ("partner_income", "DOUBLE"),
            ("coupon_id", "VARCHAR"),
            ("marketing_coupon_id", "VARCHAR"),
            ("hq_discount_raw_amount", "DOUBLE"),
            ("discount_raw_amount", "DOUBLE"),
        ],
    }
    with engine.begin() as conn:
        for table_name, columns in table_columns.items():
            try:
                existing = {
                    row["name"]
                    for row in conn.execute(text(f"PRAGMA table_info('{table_name}')")).mappings().all()
                }
            except Exception:
                continue
            for column_name, column_type in columns:
                if column_name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

        # Add composite indexes for performance optimization
        indexes_to_create = [
            ("idx_ods_order_detail_raw_month_id", "ods_order_detail_raw", ["order_month", "order_id"]),
            ("idx_dwd_order_detail_month_date", "dwd_order_detail", ["order_month", "order_date"]),
        ]

        for idx_name, table_name, columns in indexes_to_create:
            try:
                existing_indexes = {
                    row["name"]
                    for row in conn.execute(
                        text(f"PRAGMA index_list('{table_name}')")
                    ).mappings().all()
                }
                if idx_name not in existing_indexes:
                    cols = ", ".join(columns)
                    conn.execute(
                        text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({cols})")
                    )
            except Exception:
                pass


def _canonical_row(row: dict[str, Any], mapping: dict[str, list[str]]) -> dict[str, Any]:
    normalized = {normalize_header(key): value for key, value in row.items()}
    result: dict[str, Any] = {}
    for target, aliases in mapping.items():
        value = None
        for alias in aliases:
            alias_key = normalize_header(alias)
            if alias_key in normalized and clean_text(normalized[alias_key]) is not None:
                value = normalized[alias_key]
                break
        if target in IDENTIFIER_FIELDS:
            result[target] = normalize_identifier(value)
        else:
            result[target] = clean_text(value)
    return result


def _iter_source_files(settings: Settings) -> list[tuple[str, Path]]:
    order_folders = []
    orders_raw = resolve_path(settings.paths.orders_raw)
    legacy_orders = resolve_path(settings.paths.orders)
    if orders_raw.exists():
        order_folders.append(orders_raw)
    if legacy_orders.exists() and legacy_orders != orders_raw:
        order_folders.append(legacy_orders)

    folders = {
        "orders": order_folders,
        "riders": [resolve_path(settings.paths.riders)],
        "merchants": [resolve_path(settings.paths.merchants)],
        "partners": [resolve_path(settings.paths.partners)],
    }
    files: list[tuple[str, Path]] = []
    seen_paths: set[str] = set()
    for file_type, sources in folders.items():
        for folder in sources:
            if not folder.exists():
                continue
            for path in sorted(folder.iterdir()):
                if not path.is_file() or path.suffix.lower() not in {".xls", ".xlsx", ".csv"}:
                    continue
                if path.name.startswith("."):
                    continue
                resolved = str(path.resolve())
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                files.append((file_type, path))
    return files


def _is_success_registry_exists(session: Session, file_type: str, sha: str) -> bool:
    stmt = select(FileRegistry.file_id).where(
        FileRegistry.file_type == file_type,
        FileRegistry.sha256 == sha,
        FileRegistry.status == "success",
    )
    return session.scalar(stmt) is not None


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _normalize_month(value: str | None) -> str | None:
    text_value = clean_text(value)
    if not text_value:
        return None
    return text_value if MONTH_PATTERN.match(text_value) else None


def _month_sql_list(months: set[str]) -> str:
    normalized = sorted({_normalize_month(month) for month in months if _normalize_month(month)})
    return ", ".join(_sql_literal(month) for month in normalized)


def _timestamp_sql(expr: str) -> str:
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
    ]
    tries = [f"try_strptime({expr}, '{pattern}')" for pattern in patterns]
    return "COALESCE(" + ", ".join(tries) + ")"


def _amount_sql(expr: str) -> str:
    normalized = f"regexp_replace(COALESCE(CAST({expr} AS VARCHAR), ''), '[^0-9\\\\.-]', '', 'g')"
    return f"COALESCE(TRY_CAST(NULLIF({normalized}, '') AS DOUBLE), 0.0)"


def _identifier_sql(expr: str) -> str:
    compact = f"replace(replace(trim(COALESCE(CAST({expr} AS VARCHAR), '')), '　', ''), ' ', '')"
    normalized = f"regexp_replace({compact}, '\\\\.0+$', '')"
    return f"NULLIF({normalized}, '')"


def _field_expr(columns: dict[str, str], aliases: list[str]) -> str:
    candidates: list[str] = []
    for alias in aliases:
        alias_key = normalize_header(alias)
        column_name = columns.get(alias_key)
        if column_name:
            candidates.append(f"NULLIF(TRIM(CAST({_sql_identifier(column_name)} AS VARCHAR)), '')")
    if not candidates:
        return "NULL"
    return "COALESCE(" + ", ".join(candidates) + ")"


def _create_registry_running(
    session_factory,
    run_id: str,
    file_id: str,
    file_type: str,
    source_type: str,
    file_path: Path,
    sha256: str,
    stage_file_path: Path | None,
    stage_status: str,
    order_month: str | None = None,
) -> None:
    with session_scope(session_factory) as session:
        session.add(
            FileRegistry(
                file_id=file_id,
                batch_id=run_id,
                file_type=file_type,
                source_type=source_type,
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                sha256=sha256,
                order_month=order_month,
                stage_file_path=str(stage_file_path) if stage_file_path else None,
                stage_status=stage_status,
                status="running",
            )
        )


def _create_registry_failed(
    session_factory,
    run_id: str,
    file_type: str,
    source_type: str,
    file_path: Path,
    sha256: str,
    stage_status: str,
    error_message: str,
    stage_file_path: Path | None = None,
) -> None:
    with session_scope(session_factory) as session:
        session.add(
            FileRegistry(
                file_id=uuid4().hex,
                batch_id=run_id,
                file_type=file_type,
                source_type=source_type,
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                sha256=sha256,
                stage_file_path=str(stage_file_path) if stage_file_path else None,
                stage_status=stage_status,
                status="failed",
                error_message=error_message,
            )
        )


def _update_registry_status(
    session_factory,
    file_id: str,
    *,
    status: str,
    stage_status: str | None = None,
    error_message: str | None = None,
    order_month: str | None = None,
) -> None:
    with session_scope(session_factory) as session:
        item = session.get(FileRegistry, file_id)
        if not item:
            return
        item.status = status
        if stage_status is not None:
            item.stage_status = stage_status
        if error_message is not None:
            item.error_message = error_message
        if order_month is not None:
            item.order_month = order_month


def _ensure_order_stage_table(session: Session) -> None:
    session.execute(text("DROP TABLE IF EXISTS stg_order_raw"))
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS stg_order_raw (
                batch_id VARCHAR,
                file_id VARCHAR,
                source_row_number INTEGER,
                order_month VARCHAR,
                order_id VARCHAR,
                partner_id VARCHAR,
                partner_name VARCHAR,
                merchant_id VARCHAR,
                merchant_name VARCHAR,
                shop_name VARCHAR,
                user_id VARCHAR,
                rider_id VARCHAR,
                rider_name VARCHAR,
                employment_status VARCHAR,
                order_status VARCHAR,
                customer_service_id VARCHAR,
                order_source VARCHAR,
                added_at VARCHAR,
                pay_time VARCHAR,
                accept_time VARCHAR,
                cancel_time VARCHAR,
                complete_time VARCHAR,
                order_price VARCHAR,
                amount_payable VARCHAR,
                hq_discount_amount VARCHAR,
                coupon_id VARCHAR,
                marketing_coupon_id VARCHAR,
                discount_amount VARCHAR,
                amount_paid VARCHAR,
                rider_income VARCHAR,
                partner_income VARCHAR
            )
            """
        )
    )


def _record_stage_metric(
    session_factory,
    run_id: str,
    stage_name: str,
    started_at: datetime,
    ended_at: datetime,
    input_rows: int,
    output_rows: int,
    status: str,
    detail: str | None = None,
) -> None:
    duration = max((ended_at - started_at).total_seconds(), 0.0)
    with session_scope(session_factory) as session:
        session.add(
            EtlStageMetrics(
                stage_id=f"{run_id}:{stage_name.lower()}",
                run_id=run_id,
                stage_name=stage_name,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                input_rows=input_rows,
                output_rows=output_rows,
                status=status,
                detail=detail,
            )
        )


def _all_order_months(session: Session) -> set[str]:
    stmt = (
        select(OrderDetailRaw.order_month)
        .where(OrderDetailRaw.order_month.is_not(None))
        .distinct()
    )
    return {item for item in session.scalars(stmt) if _normalize_month(item)}


def _needs_order_reload(session: Session) -> bool:
    has_data = session.scalar(select(func.count()).select_from(OrderDetailRaw)) or 0
    if has_data == 0:
        return False

    has_core_fields = session.scalar(
        select(func.count())
        .select_from(OrderDetailRaw)
        .where(
            (OrderDetailRaw.order_source.is_not(None))
            | (OrderDetailRaw.accept_time.is_not(None))
            | (OrderDetailRaw.amount_paid.is_not(None))
            | (OrderDetailRaw.employment_status.is_not(None))
        )
    ) or 0

    has_income_fields = session.scalar(
        select(func.count())
        .select_from(OrderDetailRaw)
        .where(
            (OrderDetailRaw.rider_income.is_not(None))
            | (OrderDetailRaw.partner_income.is_not(None))
        )
    ) or 0

    return has_core_fields == 0 or has_income_fields == 0


def _needs_partner_region_reload(session: Session) -> bool:
    has_raw_data = session.scalar(select(func.count()).select_from(PartnerRosterRaw)) or 0
    if has_raw_data == 0:
        return False

    has_standard_data = session.scalar(select(func.count()).select_from(PartnerRoster)) or 0
    if has_standard_data == 0:
        return True

    missing_region_count = session.scalar(
        select(func.count())
        .select_from(PartnerRoster)
        .where(
            PartnerRoster.region_raw.is_not(None),
            PartnerRoster.province.is_(None),
            PartnerRoster.city.is_(None),
            PartnerRoster.district.is_(None),
        )
    ) or 0

    if missing_region_count > 0:
        parsed_count = session.scalar(
            select(func.count())
            .select_from(PartnerRoster)
            .where(
                (PartnerRoster.province.is_not(None))
                | (PartnerRoster.city.is_not(None))
                | (PartnerRoster.district.is_not(None))
            )
        ) or 0
        return parsed_count == 0

    return False


def _should_skip_success_registry(mode: str, registry_hit: bool) -> bool:
    return should_skip_success_registry(mode, registry_hit)


def _preprocess_files(
    session_factory,
    settings: Settings,
    run_id: str,
    files: list[tuple[str, Path]],
    mode: str = "auto",
) -> PreprocessOutcome:
    order_files: list[PreparedOrderFile] = []
    roster_files: list[PreparedRosterFile] = []
    skipped = 0
    errors = 0
    force_order_reload = False
    force_partner_reload = False

    with session_scope(session_factory) as session:
        force_order_reload = _needs_order_reload(session)
        force_partner_reload = _needs_partner_region_reload(session)

    for file_type, path in files:
        sha = file_sha256(path)
        with session_scope(session_factory) as session:
            should_force_reload = (file_type == "orders" and force_order_reload) or (file_type == "partners" and force_partner_reload)
            skip_by_registry = _should_skip_success_registry(mode, _is_success_registry_exists(session, file_type, sha))
            if skip_by_registry and not should_force_reload:
                skipped += 1
                continue

        try:
            file_id = uuid4().hex
            if file_type == "orders":
                source_suffix = path.suffix.lower()
                stage_dir = resolve_path(settings.paths.orders_stage)
                stage_path = stage_dir / safe_stage_name(path, sha, settings.import_config.stage_format)
                source_type = "raw_excel" if source_suffix in {".xls", ".xlsx"} else "raw_csv"
                if stage_path.exists():
                    stage_status = "reused"
                else:
                    if source_suffix in {".xls", ".xlsx"}:
                        stage_excel_to_csv(path, stage_path)
                    elif source_suffix == ".csv":
                        stage_csv_to_csv(path, stage_path)
                    else:
                        raise ValueError(f"Unsupported order file type: {path.suffix}")
                    stage_status = "created"

                inferred_month = infer_order_month_from_filename(path.name)
                _create_registry_running(
                    session_factory,
                    run_id,
                    file_id,
                    "orders",
                    source_type,
                    path,
                    sha,
                    stage_path,
                    stage_status,
                    inferred_month,
                )
                order_files.append(
                    PreparedOrderFile(
                        file_id=file_id,
                        file_path=path,
                        file_name=path.name,
                        file_size=path.stat().st_size,
                        sha256=sha,
                        source_type=source_type,
                        stage_file_path=stage_path,
                        stage_status=stage_status,
                        inferred_month=inferred_month,
                    )
                )
            else:
                _create_registry_running(
                    session_factory,
                    run_id,
                    file_id,
                    file_type,
                    "raw_excel" if path.suffix.lower() in {".xls", ".xlsx"} else "raw_csv",
                    path,
                    sha,
                    None,
                    "not_required",
                )
                roster_files.append(
                    PreparedRosterFile(
                        file_id=file_id,
                        file_type=file_type,
                        file_path=path,
                        file_name=path.name,
                        file_size=path.stat().st_size,
                        sha256=sha,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            _create_registry_failed(
                session_factory,
                run_id,
                file_type,
                "raw_excel" if path.suffix.lower() in {".xls", ".xlsx"} else "raw_csv",
                path,
                sha,
                "preprocess_failed",
                str(exc),
            )

    return PreprocessOutcome(
        order_files=order_files,
        roster_files=roster_files,
        skipped_files=skipped,
        error_files=errors,
        input_rows=len(files),
        output_rows=len(order_files),
    )


def _load_single_order_to_stage(session: Session, run_id: str, order_file: PreparedOrderFile) -> tuple[int, set[str]]:
    path_literal = _sql_literal(order_file.stage_file_path.as_posix())
    session.execute(text(f"CREATE OR REPLACE TEMP TABLE stg_source AS SELECT * FROM read_csv_auto({path_literal}, header=true, all_varchar=true, sample_size=-1)"))
    row_count = session.scalar(text("SELECT COUNT(*) FROM stg_source")) or 0
    if row_count == 0:
        return 0, set()

    columns_info = session.execute(text("PRAGMA table_info('stg_source')")).mappings().all()
    normalized_columns = {normalize_header(item["name"]): item["name"] for item in columns_info}
    expressions = {key: _field_expr(normalized_columns, aliases) for key, aliases in ORDER_FIELD_MAP.items()}
    inferred_month_sql = _sql_literal(order_file.inferred_month) if _normalize_month(order_file.inferred_month) else "NULL"
    parsed_added_sql = _timestamp_sql(expressions["added_at"])
    order_month_sql = f"COALESCE(strftime({parsed_added_sql}, '%Y-%m'), {inferred_month_sql})"

    insert_sql = f"""
        INSERT INTO stg_order_raw (
            batch_id,
            file_id,
            source_row_number,
            order_month,
            order_id,
            partner_id,
            partner_name,
            merchant_id,
            merchant_name,
            shop_name,
            user_id,
            rider_id,
            rider_name,
            employment_status,
            order_status,
            customer_service_id,
            order_source,
            added_at,
            pay_time,
            accept_time,
            cancel_time,
            complete_time,
            order_price,
            amount_payable,
            hq_discount_amount,
            coupon_id,
            marketing_coupon_id,
            discount_amount,
            amount_paid,
            rider_income,
            partner_income
        )
        SELECT
            {_sql_literal(run_id)},
            {_sql_literal(order_file.file_id)},
            CAST(row_number() OVER () + 1 AS INTEGER),
            {order_month_sql},
            {expressions["order_id"]},
            {expressions["partner_id"]},
            {expressions["partner_name"]},
            {expressions["merchant_id"]},
            {expressions["merchant_name"]},
            {expressions["shop_name"]},
            {expressions["user_id"]},
            {expressions["rider_id"]},
            {expressions["rider_name"]},
            {expressions["employment_status"]},
            {expressions["order_status"]},
            {expressions["customer_service_id"]},
            {expressions["order_source"]},
            {expressions["added_at"]},
            {expressions["pay_time"]},
            {expressions["accept_time"]},
            {expressions["cancel_time"]},
            {expressions["complete_time"]},
            {expressions["order_price"]},
            {expressions["amount_payable"]},
            {expressions["hq_discount_amount"]},
            {expressions["coupon_id"]},
            {expressions["marketing_coupon_id"]},
            {expressions["discount_amount"]},
            {expressions["amount_paid"]},
            {expressions["rider_income"]},
            {expressions["partner_income"]}
        FROM stg_source
    """
    session.execute(text(insert_sql))
    month_rows = session.execute(
        text(
            f"""
            SELECT DISTINCT order_month
            FROM stg_order_raw
            WHERE batch_id = {_sql_literal(run_id)}
              AND file_id = {_sql_literal(order_file.file_id)}
              AND order_month IS NOT NULL
            """
        )
    ).scalars()
    months = {_normalize_month(item) for item in month_rows if _normalize_month(item)}
    return int(row_count), {item for item in months if item}


def _load_stage_orders(session_factory, run_id: str, order_files: list[PreparedOrderFile]) -> LoadStageOutcome:
    success_files: list[PreparedOrderFile] = []
    errors = 0
    total_rows = 0

    with session_scope(session_factory) as session:
        _ensure_order_stage_table(session)
        session.execute(text(f"DELETE FROM stg_order_raw WHERE batch_id = {_sql_literal(run_id)}"))

    for item in order_files:
        try:
            with session_scope(session_factory) as session:
                rows, months = _load_single_order_to_stage(session, run_id, item)
            item.staged_rows = rows
            item.order_months = months
            total_rows += rows
            success_files.append(item)
            if len(months) == 1:
                order_month = next(iter(months))
            elif len(months) > 1:
                order_month = "mixed"
            else:
                order_month = _normalize_month(item.inferred_month)
            _update_registry_status(
                session_factory,
                item.file_id,
                status="running",
                stage_status="loaded",
                order_month=order_month,
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            _update_registry_status(
                session_factory,
                item.file_id,
                status="failed",
                stage_status="load_stage_failed",
                error_message=str(exc),
            )

    return LoadStageOutcome(
        success_files=success_files,
        error_files=errors,
        input_rows=len(order_files),
        output_rows=total_rows,
    )


def _import_roster_file(session: Session, run_id: str, roster_file: PreparedRosterFile, keep_raw_payload: bool) -> int:
    rows = load_table(roster_file.file_path)
    if not rows:
        return 0

    raw_model, mapping, required_field = {
        "riders": (RiderRosterRaw, RIDER_FIELD_MAP, "rider_id"),
        "merchants": (MerchantRosterRaw, MERCHANT_FIELD_MAP, "merchant_id"),
        "partners": (PartnerRosterRaw, PARTNER_FIELD_MAP, "partner_id"),
    }[roster_file.file_type]

    mappings: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        mapped = _canonical_row(row, mapping)
        if not mapped.get(required_field):
            continue
        payload = dump_json(row) if keep_raw_payload else None
        common = {
            "raw_id": f"{roster_file.file_id}:{index}",
            "file_registry_id": roster_file.file_id,
            "batch_id": run_id,
            "row_number": index,
            "imported_at": datetime.utcnow(),
            "raw_payload": payload,
        }
        common.update(mapped)
        mappings.append(common)

    if mappings:
        session.bulk_insert_mappings(raw_model, mappings)
    return len(mappings)


def _merge_ods_and_rosters(
    session_factory,
    settings: Settings,
    run_id: str,
    order_files: list[PreparedOrderFile],
    roster_files: list[PreparedRosterFile],
) -> MergeOutcome:
    touched_months: set[str] = set()
    roster_changed = False
    processed_files = 0
    errors = 0
    merged_rows = 0
    order_file_ids = [item.file_id for item in order_files]

    try:
        with session_scope(session_factory) as session:
            if order_file_ids:
                ids_sql = ", ".join(_sql_literal(file_id) for file_id in order_file_ids)
                months = session.execute(
                    text(
                        f"""
                        SELECT DISTINCT order_month
                        FROM stg_order_raw
                        WHERE batch_id = {_sql_literal(run_id)}
                          AND file_id IN ({ids_sql})
                          AND order_month IS NOT NULL
                        """
                    )
                ).scalars()
                touched_months = {item for item in (_normalize_month(value) for value in months) if item}

                if touched_months:
                    month_sql = _month_sql_list(touched_months)
                    session.execute(text(f"DELETE FROM ods_order_detail_raw WHERE order_month IN ({month_sql})"))

                session.execute(
                    text(
                        f"""
                        INSERT INTO ods_order_detail_raw (
                            raw_id,
                            file_registry_id,
                            batch_id,
                            row_number,
                            order_month,
                            imported_at,
                            order_id,
                            partner_id,
                            partner_name,
                            merchant_id,
                            merchant_name,
                            shop_name,
                            user_id,
                            rider_id,
                            rider_name,
                            employment_status,
                            order_status,
                            customer_service_id,
                            order_source,
                            added_at,
                            pay_time,
                            accept_time,
                            cancel_time,
                            complete_time,
                            order_price,
                            amount_payable,
                            hq_discount_amount,
                            coupon_id,
                            marketing_coupon_id,
                            discount_amount,
                            amount_paid,
                            rider_income,
                            partner_income,
                            raw_payload
                        )
                        SELECT
                            file_id || ':' || CAST(source_row_number AS VARCHAR),
                            file_id,
                            {_sql_literal(run_id)},
                            source_row_number,
                            order_month,
                            CURRENT_TIMESTAMP,
                            order_id,
                            partner_id,
                            partner_name,
                            merchant_id,
                            merchant_name,
                            shop_name,
                            user_id,
                            rider_id,
                            rider_name,
                            employment_status,
                            order_status,
                            customer_service_id,
                            order_source,
                            added_at,
                            pay_time,
                            accept_time,
                            cancel_time,
                            complete_time,
                            order_price,
                            amount_payable,
                            hq_discount_amount,
                            coupon_id,
                            marketing_coupon_id,
                            discount_amount,
                            amount_paid,
                            rider_income,
                            partner_income,
                            NULL
                        FROM stg_order_raw
                        WHERE batch_id = {_sql_literal(run_id)}
                          AND file_id IN ({ids_sql})
                          AND order_id IS NOT NULL
                          AND TRIM(order_id) <> ''
                        """
                    )
                )

                merged_rows = session.scalar(
                    text(
                        f"""
                        SELECT COUNT(*)
                        FROM stg_order_raw
                        WHERE batch_id = {_sql_literal(run_id)}
                          AND file_id IN ({ids_sql})
                          AND order_id IS NOT NULL
                          AND TRIM(order_id) <> ''
                        """
                    )
                ) or 0

                for item in order_files:
                    missing_count = session.scalar(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM stg_order_raw
                            WHERE batch_id = {_sql_literal(run_id)}
                              AND file_id = {_sql_literal(item.file_id)}
                              AND (order_id IS NULL OR TRIM(order_id) = '')
                            """
                        )
                    ) or 0
                    if missing_count > 0:
                        session.add(
                            AbnormalOrder(
                                abnormal_id=f"{item.file_id}:missing_order_id",
                                batch_id=run_id,
                                order_id=None,
                                file_name=item.file_name,
                                abnormal_type="missing_order_id",
                                abnormal_detail=f"{missing_count} rows missing order_id",
                            )
                        )

            for roster in roster_files:
                try:
                    inserted = _import_roster_file(session, run_id, roster, settings.import_config.keep_raw_payload)
                    _update_registry_status(session_factory, roster.file_id, status="success", stage_status="imported")
                    if inserted > 0:
                        roster_changed = True
                    processed_files += 1
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    _update_registry_status(
                        session_factory,
                        roster.file_id,
                        status="failed",
                        stage_status="merge_ods_failed",
                        error_message=str(exc),
                    )

            if roster_changed:
                rebuild_standard_tables(session)
    except Exception as exc:  # noqa: BLE001
        errors += len(order_files)
        for item in order_files:
            _update_registry_status(
                session_factory,
                item.file_id,
                status="failed",
                stage_status="merge_ods_failed",
                error_message=str(exc),
            )
        raise

    for item in order_files:
        month_value = None
        if len(item.order_months) == 1:
            month_value = next(iter(item.order_months))
        elif len(item.order_months) > 1:
            month_value = "mixed"
        elif _normalize_month(item.inferred_month):
            month_value = item.inferred_month
        _update_registry_status(
            session_factory,
            item.file_id,
            status="success",
            stage_status="merged",
            order_month=month_value,
        )
    processed_files += len(order_files)

    return MergeOutcome(
        touched_months=touched_months,
        roster_changed=roster_changed,
        processed_files=processed_files,
        error_files=errors,
        input_rows=len(order_files) + len(roster_files),
        output_rows=int(merged_rows),
    )


def rebuild_standard_tables(session: Session) -> None:
    session.execute(delete(RiderRoster))
    session.execute(delete(MerchantRoster))
    session.execute(delete(PartnerRoster))

    rider_map: dict[str, RiderRosterRaw] = {}
    merchant_map: dict[str, MerchantRosterRaw] = {}
    partner_map: dict[str, PartnerRosterRaw] = {}

    for row in session.scalars(select(RiderRosterRaw).order_by(RiderRosterRaw.imported_at, RiderRosterRaw.row_number)):
        rider_id = normalize_identifier(row.rider_id)
        if rider_id:
            rider_map[rider_id] = row
    for row in session.scalars(select(MerchantRosterRaw).order_by(MerchantRosterRaw.imported_at, MerchantRosterRaw.row_number)):
        merchant_id = normalize_identifier(row.merchant_id)
        if merchant_id:
            merchant_map[merchant_id] = row
    for row in session.scalars(select(PartnerRosterRaw).order_by(PartnerRosterRaw.imported_at, PartnerRosterRaw.row_number)):
        partner_id = normalize_identifier(row.partner_id)
        if partner_id:
            partner_map[partner_id] = row

    rider_rows = [
        {
            "rider_id": rider_id,
            "rider_name": raw.rider_name,
            "hire_date": parse_date(raw.hire_date),
            "status": raw.status,
            "partner_name": raw.partner_name,
            "region": raw.region,
            "last_updated_at": datetime.utcnow(),
        }
        for rider_id, raw in rider_map.items()
    ]
    merchant_rows = [
        {
            "merchant_id": merchant_id,
            "merchant_name": raw.merchant_name,
            "partner_name": raw.partner_name,
            "region": raw.region,
            "register_date": parse_date(raw.register_date),
            "status": raw.status,
            "last_updated_at": datetime.utcnow(),
        }
        for merchant_id, raw in merchant_map.items()
    ]
    partner_rows = []
    for partner_id, raw in partner_map.items():
        province, city, district = parse_region(raw.region_raw)
        partner_rows.append(
            {
                "partner_id": partner_id,
                "partner_name": raw.partner_name,
                "open_date": parse_date(raw.open_date),
                "region_raw": raw.region_raw,
                "province": province,
                "city": city,
                "district": district,
                "status": raw.status,
                "last_updated_at": datetime.utcnow(),
            }
        )

    if rider_rows:
        session.bulk_insert_mappings(RiderRoster, rider_rows)
    if merchant_rows:
        session.bulk_insert_mappings(MerchantRoster, merchant_rows)
    if partner_rows:
        session.bulk_insert_mappings(PartnerRoster, partner_rows)


def rebuild_dwd(session: Session, settings: Settings, order_months: set[str], batch_id: str) -> None:
    month_sql = _month_sql_list(order_months)
    if not month_sql:
        return

    session.execute(text(f"DELETE FROM dwd_order_detail WHERE order_month IN ({month_sql})"))

    create_time_sql = _timestamp_sql("r.added_at")
    pay_time_sql = _timestamp_sql("r.pay_time")
    accept_time_sql = _timestamp_sql("r.accept_time")
    cancel_time_sql = _timestamp_sql("r.cancel_time")
    complete_time_sql = _timestamp_sql("r.complete_time")
    order_price_sql = _amount_sql("r.order_price")
    amount_payable_sql = _amount_sql("r.amount_payable")
    hq_amount_sql = _amount_sql("r.hq_discount_amount")
    discount_amount_sql = _amount_sql("r.discount_amount")
    amount_paid_sql = _amount_sql("r.amount_paid")
    rider_income_sql = _amount_sql("r.rider_income")
    partner_income_sql = _amount_sql("r.partner_income")

    sql = f"""
        INSERT INTO dwd_order_detail (
            order_id, batch_id, order_month, partner_id, partner_name, merchant_id, merchant_name, user_id,
            rider_id, rider_name, shop_name, employment_status, employment_type, province, city, district,
            order_status, customer_service_id, order_source, create_time, pay_time, accept_time, cancel_time,
            complete_time, order_date, order_hour, accept_hour, is_paid, is_completed, is_cancelled,
            pay_cancel_minutes, order_elapsed_minutes_to_cancel, is_valid_order, is_valid_cancel_order,
            is_new_rider_order, is_new_merchant_order, is_new_partner_order, service_online_flag,
            is_timeout_cancel, is_not_timeout_cancel, is_unaccepted_cancel, is_accepted_cancel,
            is_rider_noliability_cancel, has_coupon_order, order_price, amount_payable, amount_paid,
            rider_income, partner_income, coupon_id, marketing_coupon_id, hq_discount_raw_amount, discount_raw_amount,
            hq_subsidy_amount, partner_subsidy_amount, is_cross_day_order
        )
        WITH latest_raw AS (
            SELECT
                r.*,
                row_number() OVER (PARTITION BY r.order_id ORDER BY r.imported_at DESC, r.row_number DESC) AS rn
            FROM ods_order_detail_raw r
            WHERE r.order_month IN ({month_sql})
              AND r.order_id IS NOT NULL
              AND TRIM(r.order_id) <> ''
        ),
        typed_raw AS (
            SELECT
                {_identifier_sql("r.order_id")} AS order_id,
                r.order_month,
                {_identifier_sql("r.partner_id")} AS partner_id,
                r.partner_name,
                {_identifier_sql("r.merchant_id")} AS merchant_id,
                r.merchant_name,
                r.shop_name,
                {_identifier_sql("r.user_id")} AS user_id,
                {_identifier_sql("r.rider_id")} AS rider_id,
                r.rider_name,
                r.employment_status,
                r.order_status,
                r.customer_service_id,
                r.order_source,
                {create_time_sql} AS create_time,
                {pay_time_sql} AS pay_time,
                {accept_time_sql} AS accept_time,
                {cancel_time_sql} AS cancel_time,
                {complete_time_sql} AS complete_time,
                {order_price_sql} AS order_price_value,
                {amount_payable_sql} AS amount_payable_value,
                {hq_amount_sql} AS hq_discount_value,
                {discount_amount_sql} AS discount_value,
                {amount_paid_sql} AS amount_paid_value,
                {rider_income_sql} AS rider_income_value,
                {partner_income_sql} AS partner_income_value,
                r.coupon_id,
                r.marketing_coupon_id
            FROM latest_raw r
            WHERE r.rn = 1
        ),
        joined AS (
            SELECT
                t.order_id,
                COALESCE(t.order_month, strftime(t.create_time, '%Y-%m')) AS order_month,
                t.partner_id,
                COALESCE(pr.partner_name, t.partner_name) AS partner_name,
                t.merchant_id,
                COALESCE(mr.merchant_name, t.merchant_name) AS merchant_name,
                t.shop_name,
                t.user_id,
                t.rider_id,
                COALESCE(rr.rider_name, t.rider_name) AS rider_name,
                t.employment_status,
                CASE
                    WHEN t.employment_status IS NOT NULL AND t.employment_status LIKE '%全职%' THEN 'fulltime'
                    WHEN t.employment_status IS NOT NULL AND t.employment_status LIKE '%兼职%' THEN 'parttime'
                    ELSE 'unknown'
                END AS employment_type,
                pr.province,
                pr.city,
                pr.district,
                t.order_status,
                t.customer_service_id,
                t.order_source,
                t.create_time,
                t.pay_time,
                t.accept_time,
                t.cancel_time,
                t.complete_time,
                CAST(t.create_time AS DATE) AS order_date,
                CAST(EXTRACT('hour' FROM t.create_time) AS INTEGER) AS order_hour,
                CAST(EXTRACT('hour' FROM t.accept_time) AS INTEGER) AS accept_hour,
                CASE WHEN t.pay_time IS NOT NULL THEN TRUE ELSE FALSE END AS is_paid,
                CASE
                    WHEN t.complete_time IS NOT NULL THEN TRUE
                    WHEN t.order_status IS NOT NULL AND (
                        t.order_status LIKE '%完成%' OR t.order_status LIKE '%送达%'
                        OR t.order_status LIKE '%已完成%' OR t.order_status LIKE '%已送达%'
                    ) THEN TRUE
                    ELSE FALSE
                END AS is_completed,
                CASE
                    WHEN t.cancel_time IS NOT NULL THEN TRUE
                    WHEN t.order_status IS NOT NULL AND t.order_status LIKE '%取消%' THEN TRUE
                    ELSE FALSE
                END AS is_cancelled,
                CASE
                    WHEN t.pay_time IS NOT NULL AND t.cancel_time IS NOT NULL
                        THEN datediff('second', t.pay_time, t.cancel_time) / 60.0
                    ELSE NULL
                END AS pay_cancel_minutes,
                CASE
                    WHEN t.create_time IS NOT NULL AND t.cancel_time IS NOT NULL
                        THEN datediff('second', t.create_time, t.cancel_time) / 60.0
                    ELSE NULL
                END AS order_elapsed_minutes_to_cancel,
                rr.hire_date AS rider_hire_date,
                mr.register_date AS merchant_register_date,
                pr.open_date AS partner_open_date,
                t.order_price_value,
                t.amount_payable_value,
                t.hq_discount_value,
                t.discount_value,
                t.amount_paid_value,
                t.rider_income_value,
                t.partner_income_value,
                t.coupon_id,
                t.marketing_coupon_id,
                CASE WHEN t.marketing_coupon_id IS NULL OR TRIM(t.marketing_coupon_id) = '' THEN FALSE ELSE TRUE END AS has_marketing_coupon
            FROM typed_raw t
            LEFT JOIN rider_roster rr ON t.rider_id = rr.rider_id
            LEFT JOIN merchant_roster mr ON t.merchant_id = mr.merchant_id
            LEFT JOIN partner_roster pr ON t.partner_id = pr.partner_id
        )
        SELECT
            j.order_id,
            {_sql_literal(batch_id)},
            j.order_month,
            j.partner_id,
            j.partner_name,
            j.merchant_id,
            j.merchant_name,
            j.user_id,
            j.rider_id,
            j.rider_name,
            j.shop_name,
            j.employment_status,
            j.employment_type,
            j.province,
            j.city,
            j.district,
            j.order_status,
            j.customer_service_id,
            j.order_source,
            j.create_time,
            j.pay_time,
            j.accept_time,
            j.cancel_time,
            j.complete_time,
            j.order_date,
            j.order_hour,
            j.accept_hour,
            j.is_paid,
            j.is_completed,
            j.is_cancelled,
            j.pay_cancel_minutes,
            j.order_elapsed_minutes_to_cancel,
            CASE
                WHEN j.is_completed THEN TRUE
                WHEN j.pay_cancel_minutes IS NOT NULL AND j.pay_cancel_minutes > {settings.business.valid_order_cancel_threshold_minutes} THEN TRUE
                ELSE FALSE
            END AS is_valid_order,
            CASE
                WHEN j.is_cancelled AND j.pay_cancel_minutes IS NOT NULL AND j.pay_cancel_minutes > {settings.business.valid_order_cancel_threshold_minutes} THEN TRUE
                ELSE FALSE
            END AS is_valid_cancel_order,
            CASE
                WHEN j.order_date IS NOT NULL AND j.rider_hire_date IS NOT NULL
                     AND datediff('day', j.rider_hire_date, j.order_date) BETWEEN 0 AND {settings.business.new_rider_window_days}
                THEN TRUE ELSE FALSE
            END AS is_new_rider_order,
            CASE
                WHEN j.order_date IS NOT NULL AND j.merchant_register_date IS NOT NULL
                     AND datediff('day', j.merchant_register_date, j.order_date) BETWEEN 0 AND {settings.business.new_merchant_window_days}
                THEN TRUE ELSE FALSE
            END AS is_new_merchant_order,
            CASE
                WHEN j.order_date IS NOT NULL AND j.partner_open_date IS NOT NULL
                     AND datediff('day', j.partner_open_date, j.order_date) BETWEEN 0 AND {settings.business.new_partner_window_days}
                THEN TRUE ELSE FALSE
            END AS is_new_partner_order,
            CASE
                WHEN EXTRACT('hour' FROM j.create_time) BETWEEN 9 AND 20 THEN TRUE
                ELSE FALSE
            END AS service_online_flag,
            CASE
                WHEN j.is_cancelled AND j.order_elapsed_minutes_to_cancel IS NOT NULL
                     AND j.order_elapsed_minutes_to_cancel > {settings.business.valid_order_cancel_threshold_minutes}
                THEN TRUE ELSE FALSE
            END AS is_timeout_cancel,
            CASE
                WHEN j.is_cancelled AND (
                    j.order_elapsed_minutes_to_cancel IS NULL
                    OR j.order_elapsed_minutes_to_cancel <= {settings.business.valid_order_cancel_threshold_minutes}
                )
                THEN TRUE ELSE FALSE
            END AS is_not_timeout_cancel,
            CASE
                WHEN j.is_cancelled AND (j.accept_time IS NULL) THEN TRUE ELSE FALSE
            END AS is_unaccepted_cancel,
            CASE
                WHEN j.is_cancelled AND (j.accept_time IS NOT NULL) THEN TRUE ELSE FALSE
            END AS is_accepted_cancel,
            CASE
                WHEN j.is_cancelled AND j.order_status IS NOT NULL AND j.order_status LIKE '%无责%' THEN TRUE ELSE FALSE
            END AS is_rider_noliability_cancel,
            CASE
                WHEN (j.coupon_id IS NOT NULL AND TRIM(j.coupon_id) <> '') OR (j.marketing_coupon_id IS NOT NULL AND TRIM(j.marketing_coupon_id) <> '') THEN TRUE
                ELSE FALSE
            END AS has_coupon_order,
            j.order_price_value,
            j.amount_payable_value,
            j.amount_paid_value,
            j.rider_income_value,
            j.partner_income_value,
            j.coupon_id,
            j.marketing_coupon_id,
            j.hq_discount_value,
            j.discount_value,
            CASE WHEN j.has_marketing_coupon THEN 0 ELSE j.hq_discount_value END AS hq_subsidy_amount,
            CASE WHEN j.has_marketing_coupon THEN j.discount_value + j.hq_discount_value ELSE j.discount_value END AS partner_subsidy_amount,
            CASE
                WHEN j.create_time IS NOT NULL AND j.complete_time IS NOT NULL
                     AND CAST(j.create_time AS DATE) <> CAST(j.complete_time AS DATE)
                THEN TRUE ELSE FALSE
            END AS is_cross_day_order
        FROM joined j
        WHERE j.order_id IS NOT NULL
          AND TRIM(j.order_id) <> ''
    """
    session.execute(text(sql))


def rebuild_ads(session: Session, order_months: set[str], batch_id: str) -> None:
    month_sql = _month_sql_list(order_months)
    if not month_sql:
        return

    for model in (
        AdsAdminDayMetrics,
        AdsAdminPartnerMetrics,
        AdsDirectCancelDayMetrics,
        AdsDirectCouponMetrics,
        AdsDirectHourMetrics,
        AdsDirectMerchantDayMetrics,
        AdsDirectNewMerchantMetrics,
        AdsDirectNewRiderMetrics,
        AdsDirectOrderSourceDayMetrics,
        AdsPartnerDayMetrics,
        AdsPartnerHourMetrics,
        AdsPartnerRiderDayMetrics,
        AdsPartnerMerchantDayMetrics,
        AdsPartnerUserMerchantMetrics,
    ):
        session.execute(delete(model).where(model.order_month.in_(sorted(order_months))))

    base_where = f"order_month IN ({month_sql}) AND order_date IS NOT NULL"

    session.execute(
        text(
            f"""
            INSERT INTO ads_admin_day_metrics (
                metric_key, order_month, batch_id, date, province, city, district,
                total_orders, valid_orders, completed_orders, cancelled_orders, completion_rate,
                active_partners, new_partners, active_merchants, new_merchants, active_riders, new_riders,
                hq_subsidy_total, partner_subsidy_total
            )
            SELECT
                concat('admin_day|', CAST(order_date AS VARCHAR), '|', COALESCE(province, ''), '|', COALESCE(city, ''), '|', COALESCE(district, '')),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                order_date,
                province,
                city,
                district,
                COUNT(*),
                SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END), 0), 0), 4),
                COUNT(DISTINCT CASE WHEN partner_id IS NOT NULL AND TRIM(partner_id) <> '' THEN partner_id END),
                COUNT(DISTINCT CASE WHEN is_new_partner_order AND partner_id IS NOT NULL AND TRIM(partner_id) <> '' THEN partner_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_merchant_order AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_rider_order AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                ROUND(SUM(hq_subsidy_amount), 2),
                ROUND(SUM(partner_subsidy_amount), 2)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 5, 6, 7
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_admin_partner_metrics (
                metric_key, order_month, batch_id, date, province, city, district, partner_id, partner_name,
                is_new_partner, total_orders, valid_orders, completed_orders, cancelled_orders, completion_rate,
                active_merchants, new_merchants, active_riders, new_riders, hq_subsidy_total, partner_subsidy_total
            )
            SELECT
                concat('admin_partner|', CAST(order_date AS VARCHAR), '|', COALESCE(partner_id, 'UNKNOWN')),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                order_date,
                MAX(province),
                MAX(city),
                MAX(district),
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                MAX(CASE WHEN is_new_partner_order THEN 1 ELSE 0 END) = 1,
                COUNT(*),
                SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END), 0), 0), 4),
                COUNT(DISTINCT CASE WHEN is_completed AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_merchant_order AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_rider_order AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                ROUND(SUM(hq_subsidy_amount), 2),
                ROUND(SUM(partner_subsidy_amount), 2)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 8
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_partner_day_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, date, province, city, district,
                total_orders, valid_orders, completed_orders, cancelled_orders, completion_rate, cancel_rate,
                active_merchants, new_merchants, active_riders, new_riders, new_rider_orders, old_rider_orders,
                new_merchant_orders, old_merchant_orders, hq_subsidy_total, partner_subsidy_total
            )
            SELECT
                concat('partner_day|', COALESCE(partner_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                order_date,
                MAX(province),
                MAX(city),
                MAX(district),
                COUNT(*),
                SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END), 0), 0), 4),
                ROUND(COALESCE(SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0), 4),
                COUNT(DISTINCT CASE WHEN is_completed AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_merchant_order AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' THEN merchant_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                COUNT(DISTINCT CASE WHEN is_completed AND is_new_rider_order AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END),
                SUM(CASE WHEN is_completed AND is_new_rider_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' AND NOT is_new_rider_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed AND is_new_merchant_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed AND merchant_id IS NOT NULL AND TRIM(merchant_id) <> '' AND NOT is_new_merchant_order THEN 1 ELSE 0 END),
                ROUND(SUM(hq_subsidy_amount), 2),
                ROUND(SUM(partner_subsidy_amount), 2)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_partner_hour_metrics (
                metric_key, order_month, batch_id, partner_id, date, hour, completed_orders, cancelled_orders, cancel_rate
            )
            SELECT
                concat('partner_hour|', COALESCE(partner_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR), '|', CAST(COALESCE(order_hour, 0) AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                order_date,
                COALESCE(order_hour, 0),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0), 4)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 5, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_partner_rider_day_metrics (
                metric_key, order_month, batch_id, partner_id, rider_id, rider_name, date,
                completed_orders, cancelled_orders, is_new_rider
            )
            SELECT
                concat('partner_rider|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(rider_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                COALESCE(rider_id, 'UNKNOWN'),
                MAX(rider_name),
                order_date,
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                MAX(CASE WHEN is_new_rider_order THEN 1 ELSE 0 END) = 1
            FROM dwd_order_detail
            WHERE {base_where}
              AND rider_id IS NOT NULL
              AND TRIM(rider_id) <> ''
            GROUP BY 1, 2, 3, 4, 5, 7
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_partner_merchant_day_metrics (
                metric_key, order_month, batch_id, partner_id, merchant_id, merchant_name, date,
                completed_orders, cancelled_orders, is_new_merchant, hq_subsidy_total, partner_subsidy_total
            )
            SELECT
                concat('partner_merchant|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(merchant_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                COALESCE(merchant_id, 'UNKNOWN'),
                MAX(merchant_name),
                order_date,
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END),
                MAX(CASE WHEN is_new_merchant_order THEN 1 ELSE 0 END) = 1,
                ROUND(SUM(hq_subsidy_amount), 2),
                ROUND(SUM(partner_subsidy_amount), 2)
            FROM dwd_order_detail
            WHERE {base_where}
              AND merchant_id IS NOT NULL
              AND TRIM(merchant_id) <> ''
            GROUP BY 1, 2, 3, 4, 5, 7
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_partner_user_merchant_metrics (
                metric_key, order_month, batch_id, partner_id, user_id, date, total_orders, completed_orders, cancelled_orders
            )
            SELECT
                concat('partner_user|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(user_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                COALESCE(user_id, 'UNKNOWN'),
                order_date,
                COUNT(*),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)
            FROM dwd_order_detail
            WHERE {base_where}
              AND user_id IS NOT NULL
              AND TRIM(user_id) <> ''
            GROUP BY 1, 2, 3, 4, 5, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_cancel_day_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, date,
                completed_orders, valid_orders, valid_cancel_orders, valid_cancel_rate,
                unaccepted_timeout_online_cancel_orders, unaccepted_timeout_offline_cancel_orders,
                unaccepted_timeout_cancel_orders, unaccepted_not_timeout_cancel_orders,
                unaccepted_cancel_orders, accepted_noliability_cancel_orders, unpaid_cancel_orders,
                total_orders, unaccepted_timeout_online_cancel_rate
            )
            SELECT
                concat('direct_cancel|', COALESCE(partner_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                order_date,
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END), 0), 0), 4),
                SUM(CASE WHEN is_unaccepted_cancel AND is_timeout_cancel AND service_online_flag THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_unaccepted_cancel AND is_timeout_cancel AND NOT service_online_flag THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_unaccepted_cancel AND is_timeout_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_unaccepted_cancel AND is_not_timeout_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_unaccepted_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_accepted_cancel AND is_rider_noliability_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_cancelled AND NOT is_paid THEN 1 ELSE 0 END),
                COUNT(*),
                ROUND(COALESCE(SUM(CASE WHEN is_unaccepted_cancel AND is_timeout_cancel AND service_online_flag THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0), 4)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_hour_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, date, hour,
                unpaid_orders, unaccepted_cancel_orders, accepted_cancel_orders, delivered_orders,
                total_orders, valid_orders, valid_cancel_orders, valid_cancel_rate, accepted_rider_count,
                parttime_completed_orders, parttime_rider_count, fulltime_completed_orders, fulltime_rider_count,
                parttime_efficiency, fulltime_efficiency
            )
            WITH order_hours AS (
                SELECT
                    strftime(order_date, '%Y-%m') AS order_month,
                    COALESCE(partner_id, 'UNKNOWN') AS partner_id,
                    MAX(partner_name) AS partner_name,
                    order_date AS date,
                    COALESCE(order_hour, 0) AS hour,
                    SUM(CASE WHEN is_cancelled AND NOT is_paid THEN 1 ELSE 0 END) AS unpaid_orders,
                    SUM(CASE WHEN is_unaccepted_cancel THEN 1 ELSE 0 END) AS unaccepted_cancel_orders,
                    SUM(CASE WHEN is_accepted_cancel THEN 1 ELSE 0 END) AS accepted_cancel_orders,
                    SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS delivered_orders,
                    COUNT(*) AS total_orders,
                    SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS valid_orders,
                    SUM(CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END) AS valid_cancel_orders,
                    SUM(CASE WHEN is_completed AND employment_type = 'parttime' THEN 1 ELSE 0 END) AS parttime_completed_orders,
                    COUNT(DISTINCT CASE WHEN is_completed AND employment_type = 'parttime' AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END) AS parttime_rider_count,
                    SUM(CASE WHEN is_completed AND employment_type = 'fulltime' THEN 1 ELSE 0 END) AS fulltime_completed_orders,
                    COUNT(DISTINCT CASE WHEN is_completed AND employment_type = 'fulltime' AND rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END) AS fulltime_rider_count
                FROM dwd_order_detail
                WHERE {base_where}
                GROUP BY 1, 2, 4, 5
            ),
            accepted_hours AS (
                SELECT
                    COALESCE(partner_id, 'UNKNOWN') AS partner_id,
                    order_date AS date,
                    COALESCE(accept_hour, 0) AS hour,
                    COUNT(DISTINCT CASE WHEN rider_id IS NOT NULL AND TRIM(rider_id) <> '' THEN rider_id END) AS accepted_rider_count
                FROM dwd_order_detail
                WHERE {base_where}
                  AND accept_time IS NOT NULL
                GROUP BY 1, 2, 3
            )
            SELECT
                concat('direct_hour|', o.partner_id, '|', CAST(o.date AS VARCHAR), '|', CAST(o.hour AS VARCHAR)),
                o.order_month,
                {_sql_literal(batch_id)},
                o.partner_id,
                o.partner_name,
                o.date,
                o.hour,
                o.unpaid_orders,
                o.unaccepted_cancel_orders,
                o.accepted_cancel_orders,
                o.delivered_orders,
                o.total_orders,
                o.valid_orders,
                o.valid_cancel_orders,
                ROUND(COALESCE(o.valid_cancel_orders * 1.0 / NULLIF(o.valid_orders, 0), 0), 4),
                COALESCE(a.accepted_rider_count, 0),
                o.parttime_completed_orders,
                o.parttime_rider_count,
                o.fulltime_completed_orders,
                o.fulltime_rider_count,
                ROUND(COALESCE(o.parttime_completed_orders * 1.0 / NULLIF(o.parttime_rider_count, 0), 0), 4),
                ROUND(COALESCE(o.fulltime_completed_orders * 1.0 / NULLIF(o.fulltime_rider_count, 0), 0), 4)
            FROM order_hours o
            LEFT JOIN accepted_hours a
              ON a.partner_id = o.partner_id
             AND a.date = o.date
             AND a.hour = o.hour
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_new_rider_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, rider_id, rider_name, hire_date,
                total_orders, completed_orders
            )
            SELECT
                concat('direct_new_rider|', strftime(d.order_date, '%Y-%m'), '|', COALESCE(d.partner_id, 'UNKNOWN'), '|', COALESCE(d.rider_id, 'UNKNOWN')),
                strftime(d.order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(d.partner_id, 'UNKNOWN'),
                MAX(d.partner_name),
                COALESCE(d.rider_id, 'UNKNOWN'),
                MAX(d.rider_name),
                MAX(rr.hire_date),
                COUNT(*),
                SUM(CASE WHEN d.is_completed THEN 1 ELSE 0 END)
            FROM dwd_order_detail d
            LEFT JOIN rider_roster rr ON d.rider_id = rr.rider_id
            WHERE {base_where.replace('order_date', 'd.order_date')}
              AND d.is_new_rider_order
              AND d.rider_id IS NOT NULL
              AND TRIM(d.rider_id) <> ''
            GROUP BY 1, 2, 3, 4, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_new_merchant_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, merchant_id, merchant_name, shop_name,
                register_date, total_orders, completed_orders, completion_rate
            )
            SELECT
                concat('direct_new_merchant|', strftime(d.order_date, '%Y-%m'), '|', COALESCE(d.partner_id, 'UNKNOWN'), '|', COALESCE(d.merchant_id, 'UNKNOWN')),
                strftime(d.order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(d.partner_id, 'UNKNOWN'),
                MAX(d.partner_name),
                COALESCE(d.merchant_id, 'UNKNOWN'),
                MAX(d.merchant_name),
                MAX(d.shop_name),
                MAX(mr.register_date),
                COUNT(*),
                SUM(CASE WHEN d.is_completed THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(CASE WHEN d.is_completed THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0), 4)
            FROM dwd_order_detail d
            LEFT JOIN merchant_roster mr ON d.merchant_id = mr.merchant_id
            WHERE {base_where.replace('order_date', 'd.order_date')}
              AND d.is_new_merchant_order
              AND d.merchant_id IS NOT NULL
              AND TRIM(d.merchant_id) <> ''
            GROUP BY 1, 2, 3, 4, 6
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_merchant_day_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, merchant_id, merchant_name, shop_name, date,
                unaccepted_cancel_orders, unaccepted_cancel_amount_paid, accepted_cancel_orders, accepted_cancel_amount_paid,
                completed_orders, completed_amount_paid, total_orders, completion_rate, avg_amount_paid
            )
            SELECT
                concat('direct_merchant|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(merchant_id, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                COALESCE(merchant_id, 'UNKNOWN'),
                MAX(merchant_name),
                MAX(shop_name),
                order_date,
                SUM(CASE WHEN is_unaccepted_cancel THEN 1 ELSE 0 END),
                ROUND(SUM(CASE WHEN is_unaccepted_cancel THEN amount_paid ELSE 0 END), 2),
                SUM(CASE WHEN is_accepted_cancel THEN 1 ELSE 0 END),
                ROUND(SUM(CASE WHEN is_accepted_cancel THEN amount_paid ELSE 0 END), 2),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                ROUND(SUM(CASE WHEN is_completed THEN amount_paid ELSE 0 END), 2),
                COUNT(*),
                ROUND(COALESCE(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0), 4),
                ROUND(COALESCE(SUM(amount_paid) * 1.0 / NULLIF(COUNT(*), 0), 0), 2)
            FROM dwd_order_detail
            WHERE {base_where}
              AND merchant_id IS NOT NULL
              AND TRIM(merchant_id) <> ''
            GROUP BY 1, 2, 3, 4, 6, 9
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_order_source_day_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, order_source, date,
                unpaid_orders, unaccepted_cancel_orders, accepted_cancel_orders, completed_orders, total_orders
            )
            SELECT
                concat('direct_source|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(order_source, 'UNKNOWN'), '|', CAST(order_date AS VARCHAR)),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                COALESCE(order_source, '鏈煡'),
                order_date,
                SUM(CASE WHEN is_cancelled AND NOT is_paid THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_unaccepted_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_accepted_cancel THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END),
                COUNT(*)
            FROM dwd_order_detail
            WHERE {base_where}
            GROUP BY 1, 2, 3, 4, 6, 7
            """
        )
    )

    session.execute(
        text(
            f"""
            INSERT INTO ads_direct_coupon_metrics (
                metric_key, order_month, batch_id, partner_id, partner_name, date, coupon_id, marketing_coupon_id,
                coupon_order_count, hq_discount_total, discount_total, total_discount
            )
            SELECT
                concat(
                    'direct_coupon|',
                    COALESCE(partner_id, 'UNKNOWN'),
                    '|',
                    CAST(order_date AS VARCHAR),
                    '|',
                    COALESCE(coupon_id, ''),
                    '|',
                    COALESCE(marketing_coupon_id, '')
                ),
                strftime(order_date, '%Y-%m'),
                {_sql_literal(batch_id)},
                COALESCE(partner_id, 'UNKNOWN'),
                MAX(partner_name),
                order_date,
                coupon_id,
                marketing_coupon_id,
                COUNT(*),
                ROUND(SUM(hq_discount_raw_amount), 2),
                ROUND(SUM(discount_raw_amount), 2),
                ROUND(SUM(hq_discount_raw_amount + discount_raw_amount), 2)
            FROM dwd_order_detail
            WHERE {base_where}
              AND has_coupon_order
              AND is_completed
            GROUP BY 1, 2, 3, 4, 6, 7, 8
            """
        )
    )


def import_all(settings: Settings, mode: str = "auto") -> ImportResult:
    mode = (mode or "auto").strip().lower()
    if mode not in {"auto", "force"}:
        raise ValueError(f"不支持的导入模式：{mode}。当前仅支持 auto / force。")

    _, session_factory = init_database(settings)
    run_id = uuid4().hex
    files = _iter_source_files(settings)

    with session_scope(session_factory) as session:
        session.add(ImportLog(run_id=run_id, total_files=len(files), status="running"))
        session.add(EtlJobRun(run_id=run_id, backend=settings.database.backend.lower(), status="running"))

    total_start = time.perf_counter()
    preprocess_seconds = 0.0
    load_stage_seconds = 0.0
    merge_ods_seconds = 0.0
    build_ads_seconds = 0.0
    publish_seconds = 0.0

    processed_files = 0
    skipped_files = 0
    error_files = 0
    touched_months: set[str] = set()
    data_version: str | None = None
    latest_ready_month: str | None = None
    status = "success"
    message = "导入完成"

    try:
        pre_started_at = datetime.utcnow()
        pre_start = time.perf_counter()
        preprocess = _preprocess_files(session_factory, settings, run_id, files, mode=mode)
        preprocess_seconds = time.perf_counter() - pre_start
        skipped_files += preprocess.skipped_files
        error_files += preprocess.error_files
        _record_stage_metric(
            session_factory,
            run_id,
            "PREPROCESS",
            pre_started_at,
            datetime.utcnow(),
            preprocess.input_rows,
            preprocess.output_rows,
            "success",
        )

        load_started_at = datetime.utcnow()
        load_start = time.perf_counter()
        load_result = _load_stage_orders(session_factory, run_id, preprocess.order_files)
        load_stage_seconds = time.perf_counter() - load_start
        error_files += load_result.error_files
        _record_stage_metric(
            session_factory,
            run_id,
            "LOAD_STAGE",
            load_started_at,
            datetime.utcnow(),
            load_result.input_rows,
            load_result.output_rows,
            "success",
        )

        merge_started_at = datetime.utcnow()
        merge_start = time.perf_counter()
        merge_result = _merge_ods_and_rosters(session_factory, settings, run_id, load_result.success_files, preprocess.roster_files)
        merge_ods_seconds = time.perf_counter() - merge_start
        touched_months.update(merge_result.touched_months)
        processed_files += merge_result.processed_files
        error_files += merge_result.error_files
        _record_stage_metric(
            session_factory,
            run_id,
            "MERGE_ODS",
            merge_started_at,
            datetime.utcnow(),
            merge_result.input_rows,
            merge_result.output_rows,
            "success",
        )

        with session_scope(session_factory) as session:
            months_to_rebuild = set(touched_months)
            if merge_result.roster_changed:
                months_to_rebuild = _all_order_months(session)
            if not months_to_rebuild:
                dwd_count = session.scalar(select(func.count()).select_from(DwdOrderDetail)) or 0
                if dwd_count == 0:
                    months_to_rebuild = _all_order_months(session)
            if not months_to_rebuild:
                admin_partner_count = session.scalar(select(func.count()).select_from(AdsAdminPartnerMetrics)) or 0
                if admin_partner_count == 0:
                    months_to_rebuild = _all_order_months(session)
            if not months_to_rebuild:
                direct_cancel_count = session.scalar(select(func.count()).select_from(AdsDirectCancelDayMetrics)) or 0
                if direct_cancel_count == 0:
                    months_to_rebuild = _all_order_months(session)

            build_started_at = datetime.utcnow()
            build_start = time.perf_counter()
            if months_to_rebuild:
                rebuild_dwd(session, settings, months_to_rebuild, run_id)
                rebuild_ads(session, months_to_rebuild, run_id)
            build_ads_seconds = time.perf_counter() - build_start
            touched_months = months_to_rebuild
        _record_stage_metric(
            session_factory,
            run_id,
            "BUILD_DWD_ADS",
            build_started_at,
            datetime.utcnow(),
            len(touched_months),
            len(touched_months),
            "success",
            ",".join(sorted(touched_months)) if touched_months else "no_month_rebuild",
        )

        publish_started_at = datetime.utcnow()
        publish_start = time.perf_counter()
        with session_scope(session_factory) as session:
            data_version, latest_ready_month = publish_data_version(session, run_id)
        publish_seconds = time.perf_counter() - publish_start
        _record_stage_metric(
            session_factory,
            run_id,
            "PUBLISH",
            publish_started_at,
            datetime.utcnow(),
            1,
            1,
            "success",
            data_version,
        )
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        message = str(exc)
        error_files += 1

    total_seconds = time.perf_counter() - total_start
    status, message = build_import_message(
        status=status,
        mode=mode,
        processed_files=processed_files,
        skipped_files=skipped_files,
        touched_months=touched_months,
        error_files=error_files,
    )

    with session_scope(session_factory) as session:
        import_log = session.get(ImportLog, run_id)
        if import_log:
            import_log.ended_at = datetime.utcnow()
            import_log.status = status
            import_log.processed_files = processed_files
            import_log.skipped_files = skipped_files
            import_log.error_files = error_files
            import_log.message = message

        job = session.get(EtlJobRun, run_id)
        if job:
            job.status = status
            job.ended_at = datetime.utcnow()
            job.total_seconds = round(total_seconds, 3)
            job.affected_months = ",".join(sorted(touched_months)) if touched_months else None
            job.error_message = message if status == "failed" else None

    return ImportResult(
        mode=mode,
        run_id=run_id,
        total_files=len(files),
        processed_files=processed_files,
        skipped_files=skipped_files,
        error_files=error_files,
        status=status,
        message=message,
        affected_months=sorted(touched_months),
        data_version=data_version,
        latest_ready_month=latest_ready_month,
        preprocess_seconds=round(preprocess_seconds, 3),
        load_stage_seconds=round(load_stage_seconds, 3),
        merge_ods_seconds=round(merge_ods_seconds, 3),
        build_ads_seconds=round(build_ads_seconds, 3),
        publish_seconds=round(publish_seconds, 3),
        total_seconds=round(total_seconds, 3),
    )


def get_latest_import_info(session: Session) -> dict[str, Any]:
    return _get_latest_import_info(session)
