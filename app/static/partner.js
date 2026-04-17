import {
  api,
  createSearchableSelect,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
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

const state = {
  partners: [],
  partnerControl: null,
  partnerId: "",
};

function baseFilters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#partnerStartDate", "#partnerEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    active_completed_threshold: requireElement("#partnerActiveThreshold").value || 1,
    valid_cancel_threshold_minutes: requireElement("#validCancelThreshold").value || 5,
  };
}

function populateFilters(meta) {
  renderSystemMeta(meta, { prefix: "partner" });
  setDateRange("#partnerStartDate", "#partnerEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#partnerSelectControl", {
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
  renderTags("#partnerConclusion", []);
  renderCards("#partnerCards", []);
  renderTags("#directSpecialTags", []);
  renderCards("#directSpecialCards", []);
  renderTags("#issueSummaryTags", []);
  setHtml("#partnerDailyChart", '<div class="empty empty-inline">请选择合伙人后查看城市经营摘要</div>');
  renderTable("#partnerFinanceTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看经营收益明细" });
  setHtml("#partnerFinanceChart", '<div class="empty empty-inline">请选择合伙人后查看经营收益趋势</div>');
}

function renderSummary(overview) {
  const summary = overview.summary || {};
  const diagnostics = overview.diagnostics || [];
  renderTags("#partnerConclusion", diagnostics);
  renderCards("#partnerCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "完成率", value: formatPercent(summary.completion_rate) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
    { label: "总部补贴", value: formatMoney(summary.hq_subsidy_total) },
    { label: "合伙人补贴", value: formatMoney(summary.partner_subsidy_total) },
  ]);
}

function renderDaily(daily) {
  const items = daily.items || [];
  renderLineChart("#partnerDailyChart", items.map((item) => item.date), [
    { name: "总订单", values: items.map((item) => item.total_orders) },
    { name: "有效订单", values: items.map((item) => item.valid_orders) },
    { name: "完成订单", values: items.map((item) => item.completed_orders) },
    { name: "取消订单", values: items.map((item) => item.cancelled_orders) },
  ]);
}

function renderFinance(daily) {
  const items = daily.items || [];
  renderLineChart("#partnerFinanceChart", items.map((item) => item.date), [
    { name: "实际收款", values: items.map((item) => item.actual_received_total) },
    { name: "骑手提成", values: items.map((item) => item.rider_commission_total) },
    { name: "经营利润", values: items.map((item) => item.partner_profit) },
  ]);
  renderTable(
    "#partnerFinanceTable",
    [
      { key: "date", label: "日期" },
      { key: "actual_received_total", label: "实际收款总额", render: formatMoney, align: "right" },
      { key: "rider_commission_total", label: "骑手提成总计", render: formatMoney, align: "right" },
      { key: "partner_income_total", label: "合伙人收入总额", render: formatMoney, align: "right" },
      { key: "partner_subsidy_total", label: "合伙人补贴总额", render: formatMoney, align: "right" },
      { key: "partner_profit", label: "经营利润", render: formatMoney, align: "right" },
      { key: "on_time_rate", label: "准时率", render: formatPercent, align: "right" },
      { key: "sla_on_time_rate", label: "SLA 履约率", render: formatPercent, align: "right" },
    ],
    items,
    { emptyText: "当前筛选范围暂无经营收益明细" },
  );
}

function renderDirectSummary(directData) {
  const summary = directData.summary || {};
  const tags = [
    `有效订单取消率 ${formatPercent(summary.valid_cancel_rate)}`,
    `SLA 履约率 ${formatPercent(summary.sla_on_time_rate)}`,
  ];
  if ((summary.cancel_rate || 0) >= 0.2) tags.push("直营取消率偏高，建议进入时段页排查高峰问题");
  renderTags("#directSpecialTags", tags);
  renderCards("#directSpecialCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "经营利润", value: formatMoney(summary.partner_profit) },
    { label: "骑手提成总计", value: formatMoney(summary.rider_commission_total) },
  ]);
}

function renderIssueSummary(overview, directData) {
  const summary = overview.summary || {};
  const directSummary = directData.summary || {};
  const tags = [];
  if ((summary.cancel_rate || 0) >= 0.2) tags.push("城市取消率偏高，建议进入时段热力与履约页查看高峰承接和热力图");
  if ((summary.on_time_rate || 0) < 0.8) tags.push("准时率偏低，建议关注小时运力和 SLA 履约率");
  if ((directSummary.valid_cancel_rate || 0) >= 0.08) tags.push("直营有效取消偏高，建议查看直营时段数据与渠道对比");
  if ((summary.new_riders || 0) > 0 || (summary.new_merchants || 0) > 0) tags.push("如需看新主体明细，请进入主体分析页");
  if (!tags.length) tags.push("当前经营整体平稳，可进入专题页查看细分模块。");
  renderTags("#issueSummaryTags", tags);
}

async function loadPage() {
  const filters = baseFilters();
  if (!filters.partner_id) {
    clearPanels();
    return;
  }
  const [overview, daily, directData] = await Promise.all([
    api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
    api(`/api/v1/partner/${filters.partner_id}/daily`, filters),
    api("/api/v1/direct/cancel-daily", filters),
  ]);
  renderSummary(overview);
  renderDaily(daily);
  renderFinance(daily);
  renderDirectSummary(directData);
  renderIssueSummary(overview, directData);
  if (new URLSearchParams(window.location.search).get("section") === "direct") {
    document.getElementById("directSpecialSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function bindEvents() {
  requireElement("#refreshPartner").addEventListener("click", () => loadPage().catch(showError));
  ["#partnerStartDate", "#partnerEndDate", "#partnerActiveThreshold", "#validCancelThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populateFilters(meta);
  bindEvents();
}

bootstrap().catch(showError);
