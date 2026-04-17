import {
  api,
  createSearchableSelect,
  formatMoney,
  formatNumber,
  renderCards,
  renderLineChart,
  renderSystemMeta,
  renderTable,
  renderTags,
  requireElement,
  setDateRange,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";

const state = { partners: [], partnerControl: null, partnerId: "" };

function baseFilters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#entitiesStartDate", "#entitiesEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    active_completed_threshold: requireElement("#entitiesActiveThreshold").value || 1,
  };
}

function riderListFlag() {
  return requireElement("#entitiesRiderListFilter").value || "all";
}

function merchantListFlag() {
  return requireElement("#entitiesMerchantListFilter").value || "all";
}

function merchantLikeThreshold() {
  return requireElement("#merchantLikeThresholdLocal").value || 20;
}

function populate(meta) {
  renderSystemMeta(meta, { prefix: "entities" });
  setDateRange("#entitiesStartDate", "#entitiesEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#entitiesPartnerControl", {
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

function yesNo(value) {
  return Number(value || 0) === 1 ? "是" : "否";
}

function clearPanels() {
  renderTags("#entitiesConclusion", []);
  renderCards("#entitiesCards", []);
  renderTable("#merchantLikeUsersTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看用户主体识别" });
  renderTable("#entitiesCommissionTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看骑手提成明细" });
  renderTable("#entitiesRiderRosterTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看骑手名单" });
  renderTable("#entitiesMerchantRosterTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看商家名单" });
}

function renderSummary(overview) {
  const summary = overview.summary || {};
  renderTags("#entitiesConclusion", [
    `新骑手数 ${formatNumber(summary.new_riders)}`,
    `新商家数 ${formatNumber(summary.new_merchants)}`,
    `活跃骑手数 ${formatNumber(summary.active_riders)}`,
    `活跃商家数 ${formatNumber(summary.active_merchants)}`,
  ]);
  renderCards("#entitiesCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
    { label: "骑手提成总计", value: formatMoney(summary.rider_commission_total) },
  ]);
}

function renderMerchantIdentity(rows) {
  renderTable(
    "#merchantLikeUsersTable",
    [
      { key: "user_id", label: "用户 ID" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
    ],
    rows || [],
    { emptyText: "当前阈值下暂无商家型用户" },
  );
}

function renderCommission(rows) {
  renderTable(
    "#entitiesCommissionTable",
    [
      { key: "rider_id", label: "骑手 ID" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "rider_commission_total", label: "骑手提成", render: formatMoney, align: "right" },
      { key: "rider_avg_commission", label: "骑手单均提成", render: formatMoney, align: "right" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无骑手提成明细" },
  );
}

function renderRiderRoster(rows) {
  renderTable(
    "#entitiesRiderRosterTable",
    [
      { key: "rider_id", label: "骑手 ID" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "hire_date", label: "入职时间" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "is_new_rider", label: "是否新骑手", render: yesNo, align: "center" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无骑手名单" },
  );
}

function renderMerchantRoster(rows) {
  renderTable(
    "#entitiesMerchantRosterTable",
    [
      { key: "merchant_id", label: "商家 ID" },
      { key: "merchant_name", label: "商家名称" },
      { key: "register_date", label: "注册时间" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "is_new_merchant", label: "是否新商家", render: yesNo, align: "center" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无商家名单" },
  );
}

async function loadMerchantIdentity(filters) {
  const merchants = await api(`/api/v1/partner/${filters.partner_id}/merchants`, {
    ...filters,
    merchant_like_threshold: merchantLikeThreshold(),
  });
  renderMerchantIdentity(merchants.merchant_like_users || []);
}

async function loadRosters(filters) {
  const [riders, merchants] = await Promise.all([
    api(`/api/v1/partner/${filters.partner_id}/riders`, { ...filters, new_flag: riderListFlag() }),
    api(`/api/v1/partner/${filters.partner_id}/merchants`, { ...filters, new_flag: merchantListFlag() }),
  ]);
  renderRiderRoster(riders.items || []);
  renderMerchantRoster(merchants.items || []);
}

async function loadPage() {
  const filters = baseFilters();
  if (!filters.partner_id) {
    clearPanels();
    return;
  }
  const [overview, newRiders, newMerchants, riderIncome] = await Promise.all([
    api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
    api(`/api/v1/partner/${filters.partner_id}/new-riders`, filters),
    api(`/api/v1/partner/${filters.partner_id}/new-merchants`, filters),
    api(`/api/v1/partner/${filters.partner_id}/income/riders`, filters),
  ]);
  renderSummary(overview);
  renderLineChart("#entitiesRiderChart", (newRiders.items || newRiders.daily || []).map((item) => item.date), [
    { name: "新骑手完成订单", values: (newRiders.items || newRiders.daily || []).map((item) => item.completed_orders) },
  ]);
  renderLineChart("#entitiesMerchantChart", (newMerchants.items || newMerchants.daily || []).map((item) => item.date), [
    { name: "新商家完成订单", values: (newMerchants.items || newMerchants.daily || []).map((item) => item.completed_orders) },
  ]);
  renderCommission(riderIncome.items || []);
  await Promise.all([loadMerchantIdentity(filters), loadRosters(filters)]);
}

function bindEvents() {
  requireElement("#refreshEntities").addEventListener("click", () => loadPage().catch(showError));
  ["#entitiesStartDate", "#entitiesEndDate", "#entitiesActiveThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
  requireElement("#merchantLikeThresholdLocal").addEventListener("change", () => {
    const filters = baseFilters();
    if (!filters.partner_id) return;
    loadMerchantIdentity(filters).catch(showError);
  });
  requireElement("#entitiesRiderListFilter").addEventListener("change", () => {
    const filters = baseFilters();
    if (!filters.partner_id) return;
    loadRosters(filters).catch(showError);
  });
  requireElement("#entitiesMerchantListFilter").addEventListener("change", () => {
    const filters = baseFilters();
    if (!filters.partner_id) return;
    loadRosters(filters).catch(showError);
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populate(meta);
  bindEvents();
}

bootstrap().catch(showError);
