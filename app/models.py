from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileRegistry(Base):
    __tablename__ = "ods_file_registry"

    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    file_type: Mapped[str] = mapped_column(String(32), index=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    stage_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stage_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(32), default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportLog(Base):
    __tablename__ = "dqc_import_log"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    skipped_files: Mapped[int] = mapped_column(Integer, default=0)
    error_files: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class EtlJobRun(Base):
    __tablename__ = "etl_job_run"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    backend: Mapped[str] = mapped_column(String(32), default="duckdb")
    status: Mapped[str] = mapped_column(String(32), default="running")
    affected_months: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class EtlStageMetrics(Base):
    __tablename__ = "etl_stage_metrics"

    stage_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    stage_name: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_rows: Mapped[int] = mapped_column(Integer, default=0)
    output_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="running")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataPublishVersion(Base):
    __tablename__ = "etl_publish_version"

    data_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    latest_ready_month: Mapped[str | None] = mapped_column(String(7), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(16), default="ready")


class AbnormalOrder(Base):
    __tablename__ = "dqc_abnormal_orders"

    abnormal_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    abnormal_type: Mapped[str] = mapped_column(String(64), index=True)
    abnormal_detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderDetailRaw(Base):
    __tablename__ = "ods_order_detail_raw"

    raw_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    file_registry_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    partner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rider_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_service_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    added_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pay_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accept_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    complete_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_payable: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hq_discount_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    marketing_coupon_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    coupon_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    discount_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_paid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rider_income: Mapped[str | None] = mapped_column(String(64), nullable=True)
    partner_income: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class RiderRosterRaw(Base):
    __tablename__ = "ods_rider_roster_raw"

    raw_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    file_registry_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    rider_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hire_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class MerchantRosterRaw(Base):
    __tablename__ = "ods_merchant_roster_raw"

    raw_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    file_registry_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class PartnerRosterRaw(Base):
    __tablename__ = "ods_partner_roster_raw"

    raw_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    file_registry_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    partner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    open_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class RiderRoster(Base):
    __tablename__ = "rider_roster"

    rider_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MerchantRoster(Base):
    __tablename__ = "merchant_roster"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PartnerRoster(Base):
    __tablename__ = "partner_roster"

    partner_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    open_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    region_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PartnerSlaConfig(Base):
    __tablename__ = "partner_sla_config"

    partner_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sla_minutes: Mapped[int] = mapped_column(Integer, default=30)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DwdOrderDetail(Base):
    __tablename__ = "dwd_order_detail"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    partner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rider_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    province: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_service_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accept_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    complete_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    order_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accept_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    pay_cancel_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_elapsed_minutes_to_cancel: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_valid_order: Mapped[bool] = mapped_column(Boolean, default=False)
    is_valid_cancel_order: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new_rider_order: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new_merchant_order: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new_partner_order: Mapped[bool] = mapped_column(Boolean, default=False)
    service_online_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    is_timeout_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    is_not_timeout_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unaccepted_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    is_accepted_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rider_noliability_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    has_coupon_order: Mapped[bool] = mapped_column(Boolean, default=False)
    order_price: Mapped[float] = mapped_column(Float, default=0.0)
    amount_payable: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    rider_income: Mapped[float] = mapped_column(Float, default=0.0)
    partner_income: Mapped[float] = mapped_column(Float, default=0.0)
    coupon_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    marketing_coupon_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hq_discount_raw_amount: Mapped[float] = mapped_column(Float, default=0.0)
    discount_raw_amount: Mapped[float] = mapped_column(Float, default=0.0)
    hq_subsidy_amount: Mapped[float] = mapped_column(Float, default=0.0)
    partner_subsidy_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_cross_day_order: Mapped[bool] = mapped_column(Boolean, default=False)


class AdsAdminDayMetrics(Base):
    __tablename__ = "ads_admin_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    province: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    active_partners: Mapped[int] = mapped_column(Integer, default=0)
    new_partners: Mapped[int] = mapped_column(Integer, default=0)
    active_merchants: Mapped[int] = mapped_column(Integer, default=0)
    new_merchants: Mapped[int] = mapped_column(Integer, default=0)
    active_riders: Mapped[int] = mapped_column(Integer, default=0)
    new_riders: Mapped[int] = mapped_column(Integer, default=0)
    hq_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)
    partner_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)


class AdsAdminPartnerMetrics(Base):
    __tablename__ = "ads_admin_partner_metrics"

    metric_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    province: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_new_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    active_merchants: Mapped[int] = mapped_column(Integer, default=0)
    new_merchants: Mapped[int] = mapped_column(Integer, default=0)
    active_riders: Mapped[int] = mapped_column(Integer, default=0)
    new_riders: Mapped[int] = mapped_column(Integer, default=0)
    hq_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)
    partner_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)


class AdsPartnerDayMetrics(Base):
    __tablename__ = "ads_partner_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cancel_rate: Mapped[float] = mapped_column(Float, default=0.0)
    active_merchants: Mapped[int] = mapped_column(Integer, default=0)
    new_merchants: Mapped[int] = mapped_column(Integer, default=0)
    active_riders: Mapped[int] = mapped_column(Integer, default=0)
    new_riders: Mapped[int] = mapped_column(Integer, default=0)
    new_rider_orders: Mapped[int] = mapped_column(Integer, default=0)
    old_rider_orders: Mapped[int] = mapped_column(Integer, default=0)
    new_merchant_orders: Mapped[int] = mapped_column(Integer, default=0)
    old_merchant_orders: Mapped[int] = mapped_column(Integer, default=0)
    hq_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)
    partner_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)


class AdsPartnerHourMetrics(Base):
    __tablename__ = "ads_partner_hour_metrics"

    metric_key: Mapped[str] = mapped_column(String(220), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    hour: Mapped[int] = mapped_column(Integer, index=True)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancel_rate: Mapped[float] = mapped_column(Float, default=0.0)


class AdsPartnerRiderDayMetrics(Base):
    __tablename__ = "ads_partner_rider_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    rider_id: Mapped[str] = mapped_column(String(64), index=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    is_new_rider: Mapped[bool] = mapped_column(Boolean, default=False)


class AdsPartnerMerchantDayMetrics(Base):
    __tablename__ = "ads_partner_merchant_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    is_new_merchant: Mapped[bool] = mapped_column(Boolean, default=False)
    hq_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)
    partner_subsidy_total: Mapped[float] = mapped_column(Float, default=0.0)


class AdsPartnerUserMerchantMetrics(Base):
    __tablename__ = "ads_partner_user_merchant_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)


class AdsDirectCancelDayMetrics(Base):
    __tablename__ = "ads_direct_cancel_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_cancel_rate: Mapped[float] = mapped_column(Float, default=0.0)
    unaccepted_timeout_online_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_timeout_offline_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_timeout_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_not_timeout_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    accepted_noliability_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unpaid_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_timeout_online_cancel_rate: Mapped[float] = mapped_column(Float, default=0.0)


class AdsDirectHourMetrics(Base):
    __tablename__ = "ads_direct_hour_metrics"

    metric_key: Mapped[str] = mapped_column(String(260), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    hour: Mapped[int] = mapped_column(Integer, index=True)
    unpaid_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    accepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    delivered_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    valid_cancel_rate: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_rider_count: Mapped[int] = mapped_column(Integer, default=0)
    parttime_completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    parttime_rider_count: Mapped[int] = mapped_column(Integer, default=0)
    fulltime_completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    fulltime_rider_count: Mapped[int] = mapped_column(Integer, default=0)
    parttime_efficiency: Mapped[float] = mapped_column(Float, default=0.0)
    fulltime_efficiency: Mapped[float] = mapped_column(Float, default=0.0)


class AdsDirectNewRiderMetrics(Base):
    __tablename__ = "ads_direct_new_rider_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rider_id: Mapped[str] = mapped_column(String(64), index=True)
    rider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)


class AdsDirectNewMerchantMetrics(Base):
    __tablename__ = "ads_direct_new_merchant_metrics"

    metric_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)


class AdsDirectMerchantDayMetrics(Base):
    __tablename__ = "ads_direct_merchant_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(260), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    unaccepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_cancel_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    accepted_cancel_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)


class AdsDirectOrderSourceDayMetrics(Base):
    __tablename__ = "ads_direct_order_source_day_metrics"

    metric_key: Mapped[str] = mapped_column(String(260), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_source: Mapped[str] = mapped_column(String(128), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    unpaid_orders: Mapped[int] = mapped_column(Integer, default=0)
    unaccepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    accepted_cancel_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)


class AdsDirectCouponMetrics(Base):
    __tablename__ = "ads_direct_coupon_metrics"

    metric_key: Mapped[str] = mapped_column(String(260), primary_key=True)
    order_month: Mapped[str | None] = mapped_column(String(7), index=True, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_id: Mapped[str] = mapped_column(String(64), index=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    coupon_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    marketing_coupon_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    coupon_order_count: Mapped[int] = mapped_column(Integer, default=0)
    hq_discount_total: Mapped[float] = mapped_column(Float, default=0.0)
    discount_total: Mapped[float] = mapped_column(Float, default=0.0)
    total_discount: Mapped[float] = mapped_column(Float, default=0.0)
