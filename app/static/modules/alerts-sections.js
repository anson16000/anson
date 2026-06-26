import {
  formatDecimal,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderTable,
  renderTags,
  setHtml,
} from "/static/common.js";

function getSharedPartnerParam() {
  try {
    const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
    const pid = data._shared_partner_id;
    const sd = data._shared_start_date;
    const ed = data._shared_end_date;
    const params = new URLSearchParams();
    if (pid) params.set("partner_id", pid);
    if (sd) params.set("start_date", sd);
    if (ed) params.set("end_date", ed);
    const text = params.toString();
    return text ? `?${text}` : "";
  } catch (_) {
    return "";
  }
}

function partnerColumns(includeScore = false) {
  const columns = [
    { key: "partner_id", label: "合伙人 ID", sortType: "string" },
    { key: "partner_name", label: "合伙人名称" },
    { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
    { key: "valid_orders", label: "有效订单", render: formatNumber, align: "right" },
    { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
    { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
    { key: "completion_rate", label: "完成率", render: formatPercent, align: "right" },
    { key: "cancel_rate", label: "取消率", render: formatPercent, align: "right" },
    { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
    { key: "active_riders", label: "骑手人数", render: formatNumber, align: "right" },
    { key: "active_merchants", label: "商家数量", render: formatNumber, align: "right" },
    { key: "avg_ticket_price", label: "订单均价", render: formatMoney, align: "right" },
    { key: "partner_profit", label: "经营利润", render: formatMoney, align: "right" },
  ];
  if (includeScore) {
    columns.push({ key: "total_score", label: "健康度评分", render: formatDecimal, align: "right" });
  }
  return columns;
}

function entityAlertEmptyText(entityAlerts, fallback) {
  if (entityAlerts?.requires_partner) {
    return entityAlerts.message || "请选择合伙人后查看商家/骑手预警";
  }
  return entityAlerts?.message || fallback;
}

export function renderAlertsSummary(metrics, health) {
  const summary = health.summary || {};
  const tags = [
    `健康 ${formatNumber(summary.green_count)} 家`,
    `关注 ${formatNumber(summary.yellow_count)} 家`,
    `风险 ${formatNumber(summary.red_count)} 家`,
    `平均健康度 ${formatDecimal(summary.average_score)}`,
  ];
  if ((summary.red_count || 0) > 0) {
    tags.push("建议优先处理风险加盟商和波动预警");
  }
  renderTags("#alertsConclusion", tags);
  setHtml("#alertsDrillLinks", `
    <a class="drill-link" href="/partner/entities${getSharedPartnerParam()}">主体分析：查看贡献结构和关键名单</a>
    <a class="drill-link" href="/partner/hourly${getSharedPartnerParam()}">时段热力：查看履约异常时段</a>
  `);
  renderCards("#alertsCards .kpi-tier-result", [
    { label: "风险加盟商", value: formatNumber(summary.red_count) },
    { label: "平均健康度", value: formatDecimal(summary.average_score) },
  ]);
  renderCards("#alertsCards .kpi-tier-process", [
    { label: "健康加盟商", value: formatNumber(summary.green_count) },
    { label: "关注加盟商", value: formatNumber(summary.yellow_count) },
  ]);
  renderCards("#alertsCards .kpi-tier-action", [
    { label: "关注清单数", value: formatNumber((metrics.focus_partner_items || []).length) },
    { label: "风险清单数", value: formatNumber((metrics.risk_partner_items || []).length) },
  ]);
}

export function renderAlertsTables(metrics, health, fluctuation, entityAlerts = {}) {
  renderTable("#alertsFocusTable", partnerColumns(true), metrics.focus_partner_items || [], { emptyText: "当前筛选范围暂无关注加盟商" });
  renderTable("#alertsRiskTable", partnerColumns(true), metrics.risk_partner_items || [], { emptyText: "当前筛选范围暂无风险加盟商" });
  renderTable(
    "#alertsHealthTable",
    [
      { key: "partner_id", label: "合伙人 ID", sortType: "string" },
      { key: "partner_name", label: "合伙人名称" },
      { key: "total_score", label: "总分", render: formatDecimal, align: "right" },
      { key: "label", label: "状态" },
      { key: "issues", label: "主要问题", render: (value) => (Array.isArray(value) ? value.join(" / ") : "") },
    ],
    health.items || [],
    { emptyText: "当前筛选范围暂无健康度详情" },
  );
  renderTable(
    "#alertsFluctuationTable",
    [
      { key: "partner_id", label: "合伙人 ID", sortType: "string" },
      { key: "partner_name", label: "合伙人名称" },
      { key: "city_level", label: "城市档位" },
      { key: "latest_completed_orders", label: "最新完成订单", render: formatNumber, align: "right" },
      { key: "baseline_completed_orders", label: "基线完成订单", render: formatDecimal, align: "right" },
      { key: "change_abs", label: "变化量", render: formatNumber, align: "right" },
      { key: "change_pct", label: "变化幅度", render: formatPercent, align: "right" },
    ],
    fluctuation.alerts || [],
    { emptyText: "当前筛选范围暂无波动预警" },
  );

  const windows = entityAlerts.compare_windows;
  setHtml(
    "#alertsEntityNote",
    windows
      ? `<div class="hint">商家/骑手预警按前后半段对比：${windows.baseline_start_date} 至 ${windows.baseline_end_date} 对比 ${windows.recent_start_date} 至 ${windows.recent_end_date}。</div>`
      : `<div class="hint">${entityAlerts.message || "请选择合伙人后查看商家/骑手预警"}</div>`,
  );

  renderTable(
    "#alertsMerchantVolumeTable",
    [
      { key: "merchant_id", label: "商家 ID", sortType: "string" },
      { key: "merchant_name", label: "商户名称" },
      { key: "baseline_completed_orders", label: "基线完成订单", render: formatNumber, align: "right" },
      { key: "recent_completed_orders", label: "近期完成订单", render: formatNumber, align: "right" },
      { key: "drop_abs", label: "下降单量", render: formatNumber, align: "right" },
      { key: "drop_pct", label: "下降比例", render: formatPercent, align: "right" },
    ],
    entityAlerts.merchant_alerts || [],
    { emptyText: entityAlertEmptyText(entityAlerts, "当前合伙人暂无商家单量预警") },
  );
  renderTable(
    "#alertsRiderVolumeTable",
    [
      { key: "rider_id", label: "骑手 ID", sortType: "string" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "baseline_completed_orders", label: "基线完成订单", render: formatNumber, align: "right" },
      { key: "recent_completed_orders", label: "近期完成订单", render: formatNumber, align: "right" },
      { key: "drop_abs", label: "下降单量", render: formatNumber, align: "right" },
      { key: "drop_pct", label: "下降比例", render: formatPercent, align: "right" },
    ],
    entityAlerts.rider_alerts || [],
    { emptyText: entityAlertEmptyText(entityAlerts, "当前合伙人暂无骑手单量预警") },
  );
  renderTable(
    "#alertsInactiveRiderTable",
    [
      { key: "rider_id", label: "骑手 ID", sortType: "string" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "last_completed_date", label: "最后完成日期", sortable: true },
      { key: "inactive_days", label: "未接单天数", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "区间完成订单", render: formatNumber, align: "right" },
    ],
    entityAlerts.inactive_riders || [],
    { emptyText: entityAlertEmptyText(entityAlerts, "当前合伙人暂无 3 天未接单骑手") },
  );
}
