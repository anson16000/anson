import {
  api,
  createSearchableSelect,
  formatDecimal,
  formatNumber,
  formatPercent,
  renderCards,
  renderHeatmap,
  renderLineChart,
  renderSystemMeta,
  renderTable,
  renderTags,
  requireElement,
  setDateRange,
  setHtml,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";

const state = { partners: [], partnerControl: null, partnerId: "" };

function filters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#hourlyStartDate", "#hourlyEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    valid_cancel_threshold_minutes: requireElement("#hourlyValidCancelThreshold").value || 5,
  };
}

function populate(meta) {
  renderSystemMeta(meta, { prefix: "hourly" });
  setDateRange("#hourlyStartDate", "#hourlyEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#hourlyPartnerControl", {
      placeholder: "输入合伙人名称或 ID 搜索",
      allLabel: "请选择",
      onChange: (value) => {
        state.partnerId = value;
        loadPage().catch(showError);
      },
    });
  }
  state.partnerControl.setOptions(
    state.partners.map((item) => ({
      value: item.partner_id,
      label: item.partner_name || item.partner_id,
      searchText: [item.partner_name, item.partner_id, item.province, item.city, item.district].filter(Boolean).join(" "),
    })),
  );
}

function clearPanels() {
  renderTags("#hourlyConclusion", []);
  renderCards("#hourlyCards", []);
  setHtml("#hourlyAcceptedChart", '<div class="empty empty-inline">请选择合伙人后查看时段运力</div>');
  renderTable("#hourlyTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看小时运力表" });
  setHtml("#hourlyCompletedHeatmap", '<div class="empty empty-inline">请选择合伙人后查看完成订单热力图</div>');
  setHtml("#hourlyCancelledHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消订单热力图</div>');
  setHtml("#hourlyCancelRateHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消率热力图</div>');
}

function renderSummary(overview, hourly) {
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
  renderCards("#hourlyCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "完成率", value: formatPercent(summary.completion_rate) },
    { label: "准时率", value: formatPercent(summary.on_time_rate) },
    { label: "SLA 履约率", value: formatPercent(summary.sla_on_time_rate) },
    { label: "SLA 超时率", value: formatPercent(summary.sla_overtime_rate) },
  ]);
}

async function loadPage() {
  const base = filters();
  if (!base.partner_id) {
    clearPanels();
    return;
  }
  const [overview, hourly] = await Promise.all([
    api(`/api/v1/partner/${base.partner_id}/overview`, base),
    api(`/api/v1/partner/${base.partner_id}/hourly`, base),
  ]);
  renderSummary(overview, hourly);
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
  renderHeatmap("#hourlyCompletedHeatmap", hourly.items || [], "completed_orders", "count");
  renderHeatmap("#hourlyCancelledHeatmap", hourly.items || [], "cancelled_orders", "cancel");
  renderHeatmap("#hourlyCancelRateHeatmap", hourly.items || [], "cancel_rate", "rate");
}

function bindEvents() {
  requireElement("#refreshHourly").addEventListener("click", () => loadPage().catch(showError));
  ["#hourlyStartDate", "#hourlyEndDate", "#hourlyValidCancelThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populate(meta);
  bindEvents();
}

bootstrap().catch(showError);
