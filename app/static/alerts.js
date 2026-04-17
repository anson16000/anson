import {
  api,
  createPartnerRegionFilterController,
  formatDecimal,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderSystemMeta,
  renderTable,
  renderTags,
  requireElement,
  setDateRange,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";

const filtersController = createPartnerRegionFilterController({
  selectors: {
    province: "#alertsProvinceControl",
    city: "#alertsCityControl",
    district: "#alertsDistrictControl",
    partner_id: "#alertsPartnerControl",
  },
  onChange: () => loadPage().catch(showError),
});

function filters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#alertsStartDate", "#alertsEndDate", 31);
  return {
    start_date: startDateText,
    end_date: endDateText,
    province: filtersController.filters.province,
    city: filtersController.filters.city,
    district: filtersController.filters.district,
    partner_id: filtersController.filters.partner_id,
    active_completed_threshold: requireElement("#alertsActiveThreshold").value || 1,
  };
}

function populate(meta) {
  renderSystemMeta(meta, { prefix: "alerts" });
  setDateRange("#alertsStartDate", "#alertsEndDate", meta.system.latest_data_date);
  filtersController.setPartners(meta.partners || []);
}

function partnerColumns(includeScore = false) {
  const columns = [
    { key: "partner_name", label: "合伙人" },
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
  if (includeScore) columns.push({ key: "total_score", label: "健康度评分", render: formatDecimal, align: "right" });
  return columns;
}

function renderSummary(metrics, health) {
  const summary = health.summary || {};
  const tags = [
    `健康 ${formatNumber(summary.green_count)} 个`,
    `关注 ${formatNumber(summary.yellow_count)} 个`,
    `风险 ${formatNumber(summary.red_count)} 个`,
    `平均健康度 ${formatDecimal(summary.average_score)}`,
  ];
  if ((summary.red_count || 0) > 0) tags.push("建议优先处理风险加盟商和波动预警");
  renderTags("#alertsConclusion", tags);
  renderCards("#alertsCards", [
    { label: "健康加盟商", value: formatNumber(summary.green_count) },
    { label: "关注加盟商", value: formatNumber(summary.yellow_count) },
    { label: "风险加盟商", value: formatNumber(summary.red_count) },
    { label: "平均健康度", value: formatDecimal(summary.average_score) },
    { label: "关注清单数", value: formatNumber((metrics.focus_partner_items || []).length) },
    { label: "风险清单数", value: formatNumber((metrics.risk_partner_items || []).length) },
  ]);
}

async function loadPage() {
  const current = filters();
  const [metrics, health, fluctuation] = await Promise.all([
    api("/api/v1/admin/metrics", current),
    api("/api/v1/admin/health", current),
    api("/api/v1/admin/partners/fluctuation", { start_date: current.start_date, end_date: current.end_date }),
  ]);
  renderSummary(metrics, health);
  renderTable("#alertsFocusTable", partnerColumns(true), metrics.focus_partner_items || [], { emptyText: "当前筛选范围暂无关注加盟商" });
  renderTable("#alertsRiskTable", partnerColumns(true), metrics.risk_partner_items || [], { emptyText: "当前筛选范围暂无风险加盟商" });
  renderTable(
    "#alertsHealthTable",
    [
      { key: "partner_name", label: "合伙人" },
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
      { key: "partner_name", label: "合伙人" },
      { key: "city_level", label: "城市档位" },
      { key: "latest_completed_orders", label: "最新完成订单", render: formatNumber, align: "right" },
      { key: "baseline_completed_orders", label: "基线完成订单", render: formatDecimal, align: "right" },
      { key: "change_abs", label: "变化量", render: formatNumber, align: "right" },
      { key: "change_pct", label: "变化幅度", render: formatPercent, align: "right" },
    ],
    fluctuation.alerts || [],
    { emptyText: "当前筛选范围暂无波动预警" },
  );
}

function bindEvents() {
  requireElement("#refreshAlerts").addEventListener("click", () => loadPage().catch(showError));
  ["#alertsStartDate", "#alertsEndDate", "#alertsActiveThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  const meta = await api("/api/v1/meta");
  populate(meta);
  bindEvents();
  await loadPage();
}

bootstrap().catch(showError);
