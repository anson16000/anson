import {
  formatDecimal,
  formatNumber,
  formatPercent,
  renderCards,
  renderHeatmap,
  renderLineChart,
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
    const str = params.toString();
    return str ? `?${str}` : "";
  } catch (_) {
    return "";
  }
}

export function renderHourlySummary(overview, hourly) {
  const summary = overview.summary || {};
  const hourSummary = hourly.hourly_summary || [];
  const peakHour = hourSummary.reduce((best, item) => (item.total_orders > (best?.total_orders || 0) ? item : best), null);
  const tags = [
    `准时率 ${formatPercent(summary.on_time_rate)}`,
    `SLA 履约率 ${formatPercent(summary.sla_on_time_rate)}`,
    `高峰接单骑手数峰值 ${formatNumber(Math.max(...hourSummary.map((item) => item.accepted_rider_count || 0), 0))}`,
  ];
  if (peakHour) tags.push(`订单高峰在 ${peakHour.hour} 点，总订单 ${formatNumber(peakHour.total_orders)}`);
  renderTags("#hourlyConclusion", tags);
  setHtml("#hourlyDrillLinks", `
    <a class="drill-link" href="/partner/entities${getSharedPartnerParam()}">主体分析：查看涉及骑手和商家明细</a>
    <a class="drill-link" href="/alerts${getSharedPartnerParam()}">诊断预警：查看异常对象和风险名单</a>
  `);
  renderCards("#hourlyCards .kpi-tier-result", [
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "完成订单/有效订单", value: formatPercent(summary.completed_orders / summary.valid_orders || 0) },
    { label: "准时率", value: formatPercent(summary.on_time_rate) },
    { label: "SLA 履约率", value: formatPercent(summary.sla_on_time_rate) },
  ]);
  renderCards("#hourlyCards .kpi-tier-process", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "SLA 超时率", value: formatPercent(summary.sla_overtime_rate) },
  ]);
}

export function renderHourlyCharts(hourly) {
  const summary = hourly.hourly_summary || [];
  renderLineChart("#hourlyAcceptedChart", summary.map((item) => `${item.hour}`), [
    { name: "接单骑手数", values: summary.map((item) => item.accepted_rider_count) },
    { name: "总订单", values: summary.map((item) => item.total_orders) },
    { name: "取消率", values: summary.map((item) => item.cancel_rate) },
  ]);
  renderTable(
    "#hourlyTable",
    [
      { key: "hour", label: "小时" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "accepted_rider_count", label: "接单骑手数", render: formatNumber, align: "right" },
      { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
      { key: "completion_rate", label: "完成率", render: formatPercent, align: "right" },
      { key: "cancel_rate", label: "取消率", render: formatPercent, align: "right" },
    ],
    summary,
    { emptyText: "当前筛选范围暂无小时运力数据" },
  );
  renderHeatmap("#hourlyCompletedHeatmap", hourly.items || [], "completed_orders", "count", { emptyText: "暂无完成订单热力图数据" });
  renderHeatmap("#hourlyCancelledHeatmap", hourly.items || [], "cancelled_orders", "cancel", { emptyText: "暂无取消订单热力图数据" });
  renderHeatmap("#hourlyCancelRateHeatmap", hourly.items || [], "cancel_rate", "rate", { emptyText: "暂无取消率热力图数据" });
}
