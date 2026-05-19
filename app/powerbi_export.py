from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.business_rules import DEFAULT_EXCLUDED_PARTNER_IDS, sql_literal
from app.config import Settings, resolve_path
from app.database import create_session_factory, session_scope


EXCLUDED_PARTNER_IDS = DEFAULT_EXCLUDED_PARTNER_IDS


@dataclass
class PowerBiExportResult:
    export_dir: str
    table_count: int
    file_count: int
    row_counts: dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0


def _sql_literal(value: str) -> str:
    return sql_literal(value)


def _copy_query_to_parquet_sql(query: str, target: Path) -> str:
    target_literal = _sql_literal(target.as_posix())
    return f"COPY ({query}) TO {target_literal} (FORMAT PARQUET, COMPRESSION SNAPPY)"


def _count_query_sql(query: str) -> str:
    return f"SELECT COUNT(*) FROM ({query}) AS export_count_source"


def _excluded_partner_list_sql() -> str:
    return ", ".join(_sql_literal(partner_id) for partner_id in EXCLUDED_PARTNER_IDS)


def _partner_not_excluded_sql(column: str = "partner_id", include_null: bool = False) -> str:
    excluded = _excluded_partner_list_sql()
    if include_null:
        return f"({column} IS NULL OR {column} NOT IN ({excluded}))"
    return f"{column} IS NOT NULL AND {column} NOT IN ({excluded})"


def _date_dimension_query() -> str:
    return f"""
        WITH bounds AS (
            SELECT MIN(date) AS min_date, MAX(date) AS max_date
            FROM ads_partner_day_metrics
            WHERE {_partner_not_excluded_sql()}
        )
        SELECT
            CAST(day_value AS DATE) AS "日期",
            CAST(EXTRACT(year FROM day_value) AS INTEGER) AS "年",
            CAST(EXTRACT(month FROM day_value) AS INTEGER) AS "月",
            CAST(EXTRACT(day FROM day_value) AS INTEGER) AS "日",
            strftime(day_value, '%Y-%m') AS "年月",
            strftime(day_value, '%m月%d日') AS "月日",
            CAST(strftime(day_value, '%w') AS INTEGER) AS "星期序号",
            CASE CAST(strftime(day_value, '%w') AS INTEGER)
                WHEN 0 THEN '周日'
                WHEN 1 THEN '周一'
                WHEN 2 THEN '周二'
                WHEN 3 THEN '周三'
                WHEN 4 THEN '周四'
                WHEN 5 THEN '周五'
                ELSE '周六'
            END AS "星期"
        FROM bounds,
             generate_series(bounds.min_date, bounds.max_date, INTERVAL 1 DAY) AS days(day_value)
        WHERE bounds.min_date IS NOT NULL AND bounds.max_date IS NOT NULL
    """


def _partner_dimension_query() -> str:
    return f"""
        WITH source AS (
            SELECT partner_id, partner_name, open_date, province, city, district, region_raw, status
            FROM partner_roster
            WHERE {_partner_not_excluded_sql()}
            UNION ALL
            SELECT partner_id, partner_name, NULL AS open_date, province, city, district, NULL AS region_raw, NULL AS status
            FROM ads_partner_day_metrics
            WHERE {_partner_not_excluded_sql()}
        )
        SELECT
            partner_id AS "合伙人ID",
            COALESCE(MAX(partner_name), partner_id) AS "合伙人名称",
            MAX(open_date) AS "开通日期",
            MAX(province) AS "省",
            MAX(city) AS "市",
            MAX(district) AS "区县",
            MAX(region_raw) AS "原始区域",
            MAX(status) AS "状态"
        FROM source
        WHERE partner_id IS NOT NULL AND TRIM(partner_id) <> ''
        GROUP BY partner_id
    """


def _rider_dimension_query() -> str:
    return """
        SELECT
            rider_id AS "骑手ID",
            COALESCE(rider_name, rider_id) AS "骑手姓名",
            hire_date AS "入职日期",
            status AS "状态",
            partner_name AS "所属合伙人",
            region AS "区域",
            last_updated_at AS "最后更新时间"
        FROM rider_roster
        WHERE rider_id IS NOT NULL AND TRIM(rider_id) <> ''
    """


def _merchant_dimension_query() -> str:
    return """
        SELECT
            merchant_id AS "商家ID",
            COALESCE(merchant_name, merchant_id) AS "商户名称",
            shop_name AS "店铺名称",
            partner_name AS "所属合伙人",
            region AS "区域",
            register_date AS "注册日期",
            status AS "状态",
            last_updated_at AS "最后更新时间"
        FROM merchant_roster
        WHERE merchant_id IS NOT NULL AND TRIM(merchant_id) <> ''
    """


def _admin_day_query() -> str:
    return f"""
        SELECT
            strftime(order_date, '%Y-%m') AS "订单月份",
            order_date AS "日期",
            province AS "省",
            city AS "市",
            district AS "区县",
            COUNT(*) AS "总订单",
            SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS "有效订单",
            SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS "完成订单",
            SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) AS "取消订单",
            COUNT(DISTINCT CASE WHEN partner_id IS NOT NULL THEN partner_id END) AS "活跃合伙人数",
            COUNT(DISTINCT CASE WHEN is_new_partner_order AND partner_id IS NOT NULL THEN partner_id END) AS "新合伙人数",
            COUNT(DISTINCT CASE WHEN is_completed AND merchant_id IS NOT NULL THEN merchant_id END) AS "活跃商家数",
            COUNT(DISTINCT CASE WHEN is_new_merchant_order AND merchant_id IS NOT NULL THEN merchant_id END) AS "新商家数",
            COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL THEN rider_id END) AS "活跃骑手数",
            COUNT(DISTINCT CASE WHEN is_new_rider_order AND rider_id IS NOT NULL THEN rider_id END) AS "新骑手数",
            ROUND(SUM(CASE WHEN is_completed THEN amount_paid ELSE 0 END), 2) AS "完成订单实付金额",
            ROUND(SUM(CASE WHEN is_completed THEN rider_income ELSE 0 END), 2) AS "骑手提成总额",
            ROUND(SUM(CASE WHEN is_completed THEN partner_income ELSE 0 END), 2) AS "合伙人收入总额",
            ROUND(SUM(hq_subsidy_amount), 2) AS "总部补贴",
            ROUND(SUM(partner_subsidy_amount), 2) AS "合伙人补贴",
            ROUND(SUM(CASE WHEN is_completed THEN partner_income ELSE 0 END) - SUM(partner_subsidy_amount), 2) AS "经营利润",
            ROUND(SUM(CASE WHEN is_completed THEN amount_paid ELSE 0 END) / NULLIF(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END), 0), 2) AS "客单价",
            ROUND(SUM(CASE WHEN is_completed THEN rider_income ELSE 0 END) / NULLIF(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END), 0), 2) AS "骑手单均提成",
            ROUND(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS "完成率",
            ROUND(SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS "取消率",
            ROUND(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL THEN rider_id END), 0), 2) AS "人效"
        FROM dwd_order_detail
        WHERE order_date IS NOT NULL AND {_partner_not_excluded_sql(include_null=True)}
        GROUP BY strftime(order_date, '%Y-%m'), order_date, province, city, district
    """


def _partner_day_query() -> str:
    return f"""
        SELECT
            strftime(order_date, '%Y-%m') AS "订单月份",
            partner_id AS "合伙人ID",
            MAX(partner_name) AS "合伙人名称",
            order_date AS "日期",
            MAX(province) AS "省",
            MAX(city) AS "市",
            MAX(district) AS "区县",
            COUNT(*) AS "总订单",
            SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS "有效订单",
            SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS "完成订单",
            SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) AS "取消订单",
            COUNT(DISTINCT CASE WHEN is_completed AND merchant_id IS NOT NULL THEN merchant_id END) AS "活跃商家数",
            COUNT(DISTINCT CASE WHEN is_new_merchant_order AND merchant_id IS NOT NULL THEN merchant_id END) AS "新商家数",
            COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL THEN rider_id END) AS "活跃骑手数",
            COUNT(DISTINCT CASE WHEN is_new_rider_order AND rider_id IS NOT NULL THEN rider_id END) AS "新骑手数",
            SUM(CASE WHEN is_completed AND is_new_rider_order THEN 1 ELSE 0 END) AS "新骑手完成订单",
            SUM(CASE WHEN is_completed AND NOT is_new_rider_order THEN 1 ELSE 0 END) AS "老骑手完成订单",
            SUM(CASE WHEN is_completed AND is_new_merchant_order THEN 1 ELSE 0 END) AS "新商家完成订单",
            SUM(CASE WHEN is_completed AND NOT is_new_merchant_order THEN 1 ELSE 0 END) AS "老商家完成订单",
            ROUND(SUM(CASE WHEN is_completed THEN amount_paid ELSE 0 END), 2) AS "完成订单实付金额",
            ROUND(SUM(CASE WHEN is_completed THEN rider_income ELSE 0 END), 2) AS "骑手提成总额",
            ROUND(SUM(CASE WHEN is_completed THEN partner_income ELSE 0 END), 2) AS "合伙人收入总额",
            ROUND(SUM(hq_subsidy_amount), 2) AS "总部补贴",
            ROUND(SUM(partner_subsidy_amount), 2) AS "合伙人补贴",
            ROUND(SUM(CASE WHEN is_completed THEN partner_income ELSE 0 END) - SUM(partner_subsidy_amount), 2) AS "经营利润",
            ROUND(SUM(CASE WHEN is_completed THEN amount_paid ELSE 0 END) / NULLIF(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END), 0), 2) AS "客单价",
            ROUND(SUM(CASE WHEN is_completed THEN rider_income ELSE 0 END) / NULLIF(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END), 0), 2) AS "骑手单均提成",
            ROUND(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS "完成率",
            ROUND(SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS "取消率",
            ROUND(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(DISTINCT CASE WHEN is_completed AND rider_id IS NOT NULL THEN rider_id END), 0), 2) AS "人效"
        FROM dwd_order_detail
        WHERE {_partner_not_excluded_sql()} AND order_date IS NOT NULL
        GROUP BY strftime(order_date, '%Y-%m'), partner_id, order_date
    """


def _partner_hour_query() -> str:
    return f"""
        WITH order_buckets AS (
            SELECT
                order_month,
                partner_id,
                MAX(partner_name) AS partner_name,
                MAX(province) AS province,
                MAX(city) AS city,
                MAX(district) AS district,
                order_date AS date,
                order_hour AS hour,
                COUNT(*) AS total_orders,
                SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS valid_orders,
                SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completed_orders,
                SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) AS cancelled_orders,
                SUM(CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END) AS valid_cancel_orders,
                SUM(CASE WHEN is_completed AND employment_type = 'fulltime' THEN 1 ELSE 0 END) AS fulltime_completed_orders,
                SUM(CASE WHEN is_completed AND employment_type = 'parttime' THEN 1 ELSE 0 END) AS parttime_completed_orders
            FROM dwd_order_detail
            WHERE {_partner_not_excluded_sql()}
              AND order_date IS NOT NULL
              AND order_hour IS NOT NULL
            GROUP BY order_month, partner_id, order_date, order_hour
        ),
        accept_buckets AS (
            SELECT
                partner_id,
                CAST(COALESCE(accept_time, create_time) AS DATE) AS date,
                accept_hour AS hour,
                COUNT(DISTINCT rider_id) AS accepted_rider_count,
                COUNT(DISTINCT CASE WHEN employment_type = 'fulltime' THEN rider_id END) AS fulltime_accepted_rider_count,
                COUNT(DISTINCT CASE WHEN employment_type = 'parttime' THEN rider_id END) AS parttime_accepted_rider_count
            FROM dwd_order_detail
            WHERE {_partner_not_excluded_sql()}
              AND rider_id IS NOT NULL
              AND accept_hour IS NOT NULL
              AND COALESCE(accept_time, create_time) IS NOT NULL
            GROUP BY partner_id, CAST(COALESCE(accept_time, create_time) AS DATE), accept_hour
        )
        SELECT
            o.order_month AS "订单月份",
            o.partner_id AS "合伙人ID",
            o.partner_name AS "合伙人名称",
            o.province AS "省",
            o.city AS "市",
            o.district AS "区县",
            o.date AS "日期",
            o.hour AS "小时",
            o.total_orders AS "总订单",
            o.valid_orders AS "有效订单",
            o.completed_orders AS "完成订单",
            o.cancelled_orders AS "取消订单",
            o.valid_cancel_orders AS "有效取消订单",
            COALESCE(a.accepted_rider_count, 0) AS "接单骑手数",
            COALESCE(a.fulltime_accepted_rider_count, 0) AS "全职接单骑手数",
            COALESCE(a.parttime_accepted_rider_count, 0) AS "兼职接单骑手数",
            o.fulltime_completed_orders AS "全职完成订单",
            o.parttime_completed_orders AS "兼职完成订单",
            CASE WHEN COALESCE(a.accepted_rider_count, 0) = 0 THEN 0
                 ELSE ROUND(o.completed_orders::DOUBLE / a.accepted_rider_count, 2)
            END AS "人效",
            CASE WHEN COALESCE(a.fulltime_accepted_rider_count, 0) = 0 THEN 0
                 ELSE ROUND(o.fulltime_completed_orders::DOUBLE / a.fulltime_accepted_rider_count, 2)
            END AS "全职人效",
            CASE WHEN COALESCE(a.parttime_accepted_rider_count, 0) = 0 THEN 0
                 ELSE ROUND(o.parttime_completed_orders::DOUBLE / a.parttime_accepted_rider_count, 2)
            END AS "兼职人效",
            CASE WHEN o.total_orders = 0 THEN 0 ELSE ROUND(o.completed_orders::DOUBLE / o.total_orders, 4) END AS "完成率",
            CASE WHEN o.total_orders = 0 THEN 0 ELSE ROUND(o.cancelled_orders::DOUBLE / o.total_orders, 4) END AS "取消率"
        FROM order_buckets o
        LEFT JOIN accept_buckets a
          ON o.partner_id = a.partner_id
         AND o.date = a.date
         AND o.hour = a.hour
    """


def _order_source_query() -> str:
    return f"""
        SELECT
            order_month AS "订单月份",
            partner_id AS "合伙人ID",
            MAX(partner_name) AS "合伙人名称",
            MAX(province) AS "省",
            MAX(city) AS "市",
            MAX(district) AS "区县",
            order_date AS "日期",
            COALESCE(NULLIF(TRIM(order_source), ''), '未知') AS "订单来源",
            COUNT(*) AS "总订单",
            SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS "有效订单",
            SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS "完成订单",
            SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) AS "取消订单",
            SUM(CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END) AS "有效取消订单"
        FROM dwd_order_detail
        WHERE {_partner_not_excluded_sql()} AND order_date IS NOT NULL
        GROUP BY order_month, partner_id, order_date, COALESCE(NULLIF(TRIM(order_source), ''), '未知')
    """


def _order_fact_query() -> str:
    return f"""
        SELECT
            order_id AS "订单编号",
            order_month AS "订单月份",
            order_date AS "日期",
            order_hour AS "下单小时",
            partner_id AS "合伙人ID",
            partner_name AS "合伙人名称",
            province AS "省",
            city AS "市",
            district AS "区县",
            merchant_id AS "商家ID",
            COALESCE(merchant_name, merchant_id) AS "商户名称",
            shop_name AS "店铺名称",
            user_id AS "用户ID",
            rider_id AS "骑手ID",
            COALESCE(rider_name, rider_id) AS "骑手姓名",
            employment_status AS "在职状态",
            employment_type AS "用工类型",
            COALESCE(NULLIF(TRIM(order_source), ''), '未知') AS "订单来源",
            order_status AS "订单状态",
            create_time AS "下单时间",
            pay_time AS "支付时间",
            accept_time AS "接单时间",
            complete_time AS "完成时间",
            cancel_time AS "取消时间",
            CASE WHEN is_paid THEN 1 ELSE 0 END AS "已支付订单数",
            CASE WHEN is_completed THEN 1 ELSE 0 END AS "完成订单数",
            CASE WHEN is_cancelled THEN 1 ELSE 0 END AS "取消订单数",
            CASE WHEN is_valid_order THEN 1 ELSE 0 END AS "有效订单数",
            CASE WHEN is_valid_cancel_order THEN 1 ELSE 0 END AS "有效取消订单数",
            CASE WHEN is_new_rider_order THEN 1 ELSE 0 END AS "新骑手订单数",
            CASE WHEN is_new_merchant_order THEN 1 ELSE 0 END AS "新商家订单数",
            CASE WHEN is_new_partner_order THEN 1 ELSE 0 END AS "新合伙人订单数",
            CASE WHEN is_timeout_cancel THEN 1 ELSE 0 END AS "超时取消订单数",
            CASE WHEN is_unaccepted_cancel THEN 1 ELSE 0 END AS "未接单取消订单数",
            CASE WHEN is_accepted_cancel THEN 1 ELSE 0 END AS "已接单取消订单数",
            CASE WHEN is_cross_day_order THEN 1 ELSE 0 END AS "跨天订单数",
            pay_cancel_minutes AS "支付到取消分钟数",
            order_elapsed_minutes_to_cancel AS "下单到取消分钟数",
            ROUND(order_price, 2) AS "订单原价",
            ROUND(amount_payable, 2) AS "应付金额",
            ROUND(amount_paid, 2) AS "实付金额",
            ROUND(rider_income, 2) AS "骑手提成",
            ROUND(partner_income, 2) AS "合伙人收入",
            ROUND(hq_income, 2) AS "总部收入",
            ROUND(maiyatian_income, 2) AS "麦芽田收入",
            ROUND(insurance_fee, 2) AS "保险费",
            ROUND(hq_income - maiyatian_income, 2) AS "系统佣金收入",
            ROUND(hq_subsidy_amount, 2) AS "总部补贴",
            ROUND(partner_subsidy_amount, 2) AS "合伙人补贴"
        FROM dwd_order_detail
        WHERE order_id IS NOT NULL AND {_partner_not_excluded_sql(include_null=True)}
    """


def _partner_health_query() -> str:
    return f"""
        SELECT
            partner_id AS "合伙人ID",
            MAX(partner_name) AS "合伙人名称",
            MAX(province) AS "省",
            MAX(city) AS "市",
            MAX(district) AS "区县",
            MIN(date) AS "开始日期",
            MAX(date) AS "结束日期",
            COUNT(DISTINCT date) AS "统计天数",
            SUM(total_orders) AS "总订单",
            SUM(valid_orders) AS "有效订单",
            SUM(completed_orders) AS "完成订单",
            SUM(cancelled_orders) AS "取消订单",
            SUM(active_riders) AS "活跃骑手日数",
            SUM(active_merchants) AS "活跃商家日数",
            ROUND(SUM(completed_orders)::DOUBLE / NULLIF(COUNT(DISTINCT date), 0), 2) AS "日均完成订单",
            ROUND(SUM(completed_orders)::DOUBLE / NULLIF(SUM(total_orders), 0), 4) AS "完成率",
            ROUND(SUM(cancelled_orders)::DOUBLE / NULLIF(SUM(total_orders), 0), 4) AS "取消率",
            ROUND(SUM(completed_orders)::DOUBLE / NULLIF(SUM(active_riders), 0), 2) AS "人效",
            CASE
                WHEN SUM(total_orders) = 0 THEN '红色风险'
                WHEN SUM(completed_orders)::DOUBLE / NULLIF(SUM(total_orders), 0) < 0.60 THEN '红色风险'
                WHEN SUM(cancelled_orders)::DOUBLE / NULLIF(SUM(total_orders), 0) > 0.30 THEN '红色风险'
                WHEN SUM(completed_orders)::DOUBLE / NULLIF(SUM(total_orders), 0) < 0.80 THEN '黄色关注'
                WHEN SUM(cancelled_orders)::DOUBLE / NULLIF(SUM(total_orders), 0) > 0.20 THEN '黄色关注'
                ELSE '绿色正常'
            END AS "健康状态"
        FROM ads_partner_day_metrics
        WHERE {_partner_not_excluded_sql()}
        GROUP BY partner_id
    """


def _partner_fluctuation_query() -> str:
    return f"""
        WITH daily AS (
            SELECT
                partner_id,
                partner_name,
                province,
                city,
                district,
                date,
                completed_orders,
                LAG(completed_orders) OVER (PARTITION BY partner_id ORDER BY date) AS previous_completed_orders
            FROM ads_partner_day_metrics
            WHERE {_partner_not_excluded_sql()}
        )
        SELECT
            partner_id AS "合伙人ID",
            partner_name AS "合伙人名称",
            province AS "省",
            city AS "市",
            district AS "区县",
            date AS "日期",
            completed_orders AS "完成订单",
            previous_completed_orders AS "前一日完成订单",
            completed_orders - COALESCE(previous_completed_orders, 0) AS "变化单量",
            CASE WHEN COALESCE(previous_completed_orders, 0) = 0 THEN NULL
                 ELSE ROUND((completed_orders - previous_completed_orders)::DOUBLE / previous_completed_orders, 4)
            END AS "变化比例",
            CASE
                WHEN previous_completed_orders IS NULL THEN '无基准'
                WHEN completed_orders < previous_completed_orders AND previous_completed_orders - completed_orders >= 100 THEN '大幅下滑'
                WHEN completed_orders < previous_completed_orders AND (previous_completed_orders - completed_orders)::DOUBLE / NULLIF(previous_completed_orders, 0) >= 0.2 THEN '比例下滑'
                ELSE '正常'
            END AS "波动类型"
        FROM daily
    """


def _partner_risk_query() -> str:
    return """
        SELECT
            "合伙人ID",
            "合伙人名称",
            "省",
            "市",
            "区县",
            "开始日期",
            "结束日期",
            "总订单",
            "完成订单",
            "取消订单",
            "完成率",
            "取消率",
            "人效",
            "健康状态",
            CASE
                WHEN "健康状态" = '红色风险' THEN 1
                WHEN "健康状态" = '黄色关注' THEN 2
                ELSE 3
            END AS "优先级",
            CASE
                WHEN "健康状态" = '红色风险' AND "完成率" < 0.60 THEN '完成率偏低，优先排查取消和履约'
                WHEN "健康状态" = '红色风险' AND "取消率" > 0.30 THEN '取消率偏高，优先排查接单和商家出餐'
                WHEN "人效" < 3 THEN '人效偏低，关注骑手排班和订单密度'
                WHEN "完成订单" < 100 THEN '单量偏低，关注商家激活和订单来源'
                WHEN "健康状态" = '黄色关注' THEN '轻度异常，建议持续跟踪'
                ELSE '正常'
            END AS "建议动作"
        FROM (
            """ + _partner_health_query() + """
        ) h
        WHERE "健康状态" IN ('红色风险', '黄色关注') OR "完成订单" < 100
    """


def _meta_data_version_query() -> str:
    return """
        SELECT
            data_version AS "数据版本",
            run_id AS "导入批次ID",
            latest_ready_month AS "最新可用月份",
            published_at AS "发布时间",
            status AS "状态"
        FROM etl_publish_version
        ORDER BY published_at DESC
        LIMIT 1
    """


POWERBI_EXPORTS: dict[str, str] = {
    "日期维度.parquet": _date_dimension_query(),
    "合伙人维度.parquet": _partner_dimension_query(),
    "骑手维度.parquet": _rider_dimension_query(),
    "商家维度.parquet": _merchant_dimension_query(),
    "全国日汇总.parquet": _admin_day_query(),
    "合伙人日汇总.parquet": _partner_day_query(),
    "小时运力汇总.parquet": _partner_hour_query(),
    "骑手日汇总.parquet": """
        SELECT
            r.order_month AS "订单月份",
            r.partner_id AS "合伙人ID",
            r.rider_id AS "骑手ID",
            COALESCE(r.rider_name, r.rider_id) AS "骑手姓名",
            r.date AS "日期",
            r.completed_orders AS "完成订单",
            r.cancelled_orders AS "取消订单",
            r.is_new_rider AS "是否新骑手",
            rr.hire_date AS "入职日期",
            rr.status AS "骑手状态",
            rr.partner_name AS "名单所属合伙人",
            rr.region AS "骑手区域"
        FROM ads_partner_rider_day_metrics r
        LEFT JOIN rider_roster rr ON r.rider_id = rr.rider_id
        WHERE r.partner_id IS NOT NULL AND r.partner_id NOT IN ('101')
    """,
    "商家日汇总.parquet": """
        SELECT
            m.order_month AS "订单月份",
            m.partner_id AS "合伙人ID",
            m.merchant_id AS "商家ID",
            COALESCE(m.merchant_name, m.merchant_id) AS "商户名称",
            m.date AS "日期",
            m.completed_orders AS "完成订单",
            m.cancelled_orders AS "取消订单",
            m.is_new_merchant AS "是否新商家",
            m.hq_subsidy_total AS "总部补贴",
            m.partner_subsidy_total AS "合伙人补贴",
            mr.shop_name AS "店铺名称",
            mr.register_date AS "注册日期",
            mr.status AS "商家状态",
            mr.partner_name AS "名单所属合伙人",
            mr.region AS "商家区域"
        FROM ads_partner_merchant_day_metrics m
        LEFT JOIN merchant_roster mr ON m.merchant_id = mr.merchant_id
        WHERE m.partner_id IS NOT NULL AND m.partner_id NOT IN ('101')
    """,
    "订单明细事实表.parquet": _order_fact_query(),
    "订单来源汇总.parquet": _order_source_query(),
    "用户商家识别汇总.parquet": """
        SELECT
            order_month AS "订单月份",
            partner_id AS "合伙人ID",
            user_id AS "用户ID",
            date AS "日期",
            total_orders AS "总订单",
            completed_orders AS "完成订单",
            cancelled_orders AS "取消订单"
        FROM ads_partner_user_merchant_metrics
        WHERE partner_id IS NOT NULL AND partner_id NOT IN ('101')
    """,
    "合伙人健康度.parquet": _partner_health_query(),
    "合伙人波动预警.parquet": _partner_fluctuation_query(),
    "合伙人风险建议.parquet": _partner_risk_query(),
    "数据版本.parquet": _meta_data_version_query(),
}


def _prepare_export_directory(final_dir: Path) -> Path:
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = final_dir.parent / f".{final_dir.name}.tmp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _replace_export_directory(temp_dir: Path, final_dir: Path) -> None:
    backup_dir = final_dir.parent / f".{final_dir.name}.backup_{uuid4().hex[:8]}"
    try:
        if final_dir.exists():
            final_dir.rename(backup_dir)
        temp_dir.rename(final_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if backup_dir.exists() and not final_dir.exists():
            backup_dir.rename(final_dir)
        raise


def export_powerbi_parquet(settings: Settings, session_factory: Any | None = None) -> PowerBiExportResult:
    started = time.perf_counter()
    final_dir = resolve_path(settings.paths.powerbi_parquet)
    temp_dir = _prepare_export_directory(final_dir)
    owns_factory = session_factory is None
    engine = None
    if session_factory is None:
        engine, session_factory = create_session_factory(settings, read_only=True)

    row_counts: dict[str, int] = {}
    try:
        with session_scope(session_factory) as session:
            for file_name, query in POWERBI_EXPORTS.items():
                cleaned_query = query.strip().rstrip(";")
                target = temp_dir / file_name
                row_count = session.scalar(text(_count_query_sql(cleaned_query))) or 0
                session.execute(text(_copy_query_to_parquet_sql(cleaned_query, target)))
                row_counts[file_name] = int(row_count)
        _replace_export_directory(temp_dir, final_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    finally:
        if owns_factory and engine is not None:
            engine.dispose()

    return PowerBiExportResult(
        export_dir=str(final_dir),
        table_count=len(POWERBI_EXPORTS),
        file_count=len(POWERBI_EXPORTS),
        row_counts=row_counts,
        duration_seconds=round(time.perf_counter() - started, 3),
    )
