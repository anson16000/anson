import {
  formatDecimal,
  formatNumber,
  renderCards,
  renderHeatmap,
  renderTable,
  renderTags,
  setHtml,
} from "/static/common.js";

const DEFAULT_TARGETS = {
  conclusion: "#workforceConclusion",
  riderCards: "#workforceCards .kpi-tier-result",
  efficiencyCards: "#workforceCards .kpi-tier-process",
  totalRiderHeatmap: "#workforceTotalRiderHeatmap",
  fulltimeRiderHeatmap: "#workforceFulltimeRiderHeatmap",
  parttimeRiderHeatmap: "#workforceParttimeRiderHeatmap",
  totalEfficiencyHeatmap: "#workforceTotalEfficiencyHeatmap",
  fulltimeEfficiencyHeatmap: "#workforceFulltimeEfficiencyHeatmap",
  parttimeEfficiencyHeatmap: "#workforceParttimeEfficiencyHeatmap",
  hourlyTable: "#workforceHourlyTable",
};

function maxOf(items, key) {
  return Math.max(...(items || []).map((item) => Number(item[key] || 0)), 0);
}

function sumOf(items, key) {
  return (items || []).reduce((total, item) => total + Number(item[key] || 0), 0);
}

function weightedEfficiency(completedOrders, riderCount) {
  if (!riderCount) return 0;
  return completedOrders / riderCount;
}

export function renderWorkforceSummary(hourly, targets = DEFAULT_TARGETS) {
  const summary = hourly.hourly_summary || [];
  const fulltimePeak = maxOf(summary, "fulltime_accepted_rider_count");
  const parttimePeak = maxOf(summary, "parttime_accepted_rider_count");
  const totalPeak = maxOf(summary, "accepted_rider_count");
  const fulltimeOrders = sumOf(summary, "fulltime_completed_orders");
  const parttimeOrders = sumOf(summary, "parttime_completed_orders");
  const fulltimeRiders = sumOf(summary, "fulltime_accepted_rider_count");
  const parttimeRiders = sumOf(summary, "parttime_accepted_rider_count");

  renderTags(targets.conclusion, [
    `总接单骑手数峰值 ${formatNumber(totalPeak)}`,
    `全职接单骑手数峰值 ${formatNumber(fulltimePeak)}`,
    `兼职接单骑手数峰值 ${formatNumber(parttimePeak)}`,
    fulltimePeak >= parttimePeak ? "高峰承接以全职为主" : "高峰承接以兼职为主",
  ]);

  renderCards(targets.riderCards, [
    { label: "总接单骑手数峰值", value: formatNumber(totalPeak) },
    { label: "全职接单骑手数峰值", value: formatNumber(fulltimePeak) },
    { label: "兼职接单骑手数峰值", value: formatNumber(parttimePeak) },
  ]);

  renderCards(targets.efficiencyCards, [
    { label: "全职人效", value: formatDecimal(weightedEfficiency(fulltimeOrders, fulltimeRiders)) },
    { label: "兼职人效", value: formatDecimal(weightedEfficiency(parttimeOrders, parttimeRiders)) },
    { label: "全职/兼职完成单量", value: `${formatNumber(fulltimeOrders)} / ${formatNumber(parttimeOrders)}` },
  ]);
}

export function renderWorkforceHeatmaps(hourly, targets = DEFAULT_TARGETS) {
  const items = hourly.items || [];
  const dailyTotalOptions = {
    dailyTotals: hourly.daily_summary || [],
    dailyTotalLabel: "人数合计",
    showDailyTotal: true,
  };
  renderHeatmap(targets.totalRiderHeatmap, items, "accepted_rider_count", "count", { emptyText: "暂无总接单骑手数热力图数据", ...dailyTotalOptions });
  renderHeatmap(targets.fulltimeRiderHeatmap, items, "fulltime_accepted_rider_count", "count", { emptyText: "暂无全职接单骑手数热力图数据", ...dailyTotalOptions });
  renderHeatmap(targets.parttimeRiderHeatmap, items, "parttime_accepted_rider_count", "count", { emptyText: "暂无兼职接单骑手数热力图数据", ...dailyTotalOptions });
  renderHeatmap(targets.totalEfficiencyHeatmap, items, "efficiency", "decimal", { emptyText: "暂无总人效热力图数据" });
  renderHeatmap(targets.fulltimeEfficiencyHeatmap, items, "fulltime_efficiency", "decimal", { emptyText: "暂无全职人效热力图数据" });
  renderHeatmap(targets.parttimeEfficiencyHeatmap, items, "parttime_efficiency", "decimal", { emptyText: "暂无兼职人效热力图数据" });
}

export function renderWorkforceTable(hourly, targets = DEFAULT_TARGETS) {
  const rows = (hourly.items || []).map((item) => ({
    ...item,
    date_hour: `${item.date || "-"} ${String(item.hour ?? "").padStart(2, "0")}:00`,
  }));

  renderTable(
    targets.hourlyTable,
    [
      { key: "date_hour", label: "日期 / 小时" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "accepted_rider_count", label: "总接单骑手数", render: formatNumber, align: "right" },
      { key: "fulltime_accepted_rider_count", label: "全职接单骑手数", render: formatNumber, align: "right" },
      { key: "parttime_accepted_rider_count", label: "兼职接单骑手数", render: formatNumber, align: "right" },
      { key: "efficiency", label: "总人效", render: formatDecimal, align: "right" },
      { key: "fulltime_efficiency", label: "全职人效", render: formatDecimal, align: "right" },
      { key: "parttime_efficiency", label: "兼职人效", render: formatDecimal, align: "right" },
      { key: "fulltime_completed_orders", label: "全职完成订单", render: formatNumber, align: "right" },
      { key: "parttime_completed_orders", label: "兼职完成订单", render: formatNumber, align: "right" },
    ],
    rows,
    { emptyText: "当前筛选范围暂无全职兼职日期小时明细数据" },
  );
}

export function clearWorkforcePanels(targets = DEFAULT_TARGETS) {
  setHtml(targets.conclusion, "");
  setHtml(targets.riderCards, "");
  setHtml(targets.efficiencyCards, "");
  setHtml(targets.totalRiderHeatmap, '<div class="empty empty-inline">请选择合伙人后查看总接单骑手数热力图</div>');
  setHtml(targets.fulltimeRiderHeatmap, '<div class="empty empty-inline">请选择合伙人后查看全职接单骑手数热力图</div>');
  setHtml(targets.parttimeRiderHeatmap, '<div class="empty empty-inline">请选择合伙人后查看兼职接单骑手数热力图</div>');
  setHtml(targets.totalEfficiencyHeatmap, '<div class="empty empty-inline">请选择合伙人后查看总人效热力图</div>');
  setHtml(targets.fulltimeEfficiencyHeatmap, '<div class="empty empty-inline">请选择合伙人后查看全职人效热力图</div>');
  setHtml(targets.parttimeEfficiencyHeatmap, '<div class="empty empty-inline">请选择合伙人后查看兼职人效热力图</div>');
  setHtml(targets.hourlyTable, '<div class="empty empty-inline">请选择合伙人后查看小时汇总表</div>');
}
