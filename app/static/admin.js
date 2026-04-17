import {
  api,
  createPartnerRegionFilterController,
  formatDecimal,
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
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";

const filtersController = createPartnerRegionFilterController({
  selectors: {
    province: "#adminProvinceControl",
    city: "#adminCityControl",
    district: "#adminDistrictControl",
    partner_id: "#adminPartnerControl",
  },
  onChange: () => loadPage().catch(showError),
});

function parseTierText(value) {
  const raw = String(value || "").trim();
  if (!raw) return [];
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      if (item.endsWith("+")) {
        const min = Number(item.slice(0, -1));
        return Number.isFinite(min) ? { label: `${min}+`, min, max: null } : null;
      }
      const match = item.match(/^(\d+)\s*-\s*(\d+)$/);
      if (!match) return null;
      return { label: `${match[1]}-${match[2]}`, min: Number(match[1]), max: Number(match[2]) };
    })
    .filter(Boolean);
}

function baseFilters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#adminStartDate", "#adminEndDate", 31);
  const tiers = parseTierText(requireElement("#partnerTierInput").value);
  return {
    start_date: startDateText,
    end_date: endDateText,
    province: filtersController.filters.province,
    city: filtersController.filters.city,
    district: filtersController.filters.district,
    partner_id: filtersController.filters.partner_id,
    active_completed_threshold: requireElement("#activeCompletedThreshold").value || 1,
    ranking_level: requireElement("#rankingLevel").value || "all",
    partner_tiers: tiers.length ? JSON.stringify(tiers) : "",
  };
}

function populateFilters(meta) {
  renderSystemMeta(meta, { prefix: "admin" });
  setDateRange("#adminStartDate", "#adminEndDate", meta.system.latest_data_date);
  filtersController.setPartners(meta.partners || []);
}

function renderConclusion(metrics) {
  const summary = metrics.summary || {};
  const tags = [
    `当前查询范围总订单 ${formatNumber(summary.total_orders)} 单`,
    `完成率 ${formatPercent(summary.completion_rate)}`,
    `取消率 ${formatPercent(summary.cancel_rate)}`,
  ];
  if ((summary.valid_completion_rate || 0) < 0.8) tags.push("有效订单完成率仍有提升空间");
  if ((summary.new_partners || 0) > 0) tags.push(`新合伙人 ${formatNumber(summary.new_partners)} 个，可继续跟进首月表现`);
  renderTags("#adminConclusion", tags);
}

function renderSummaryCards(metrics) {
  const summary = metrics.summary || {};
  renderCards("#adminCards", [
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

function renderRegionRanking(rows) {
  renderTable(
    "#regionRankingTable",
    [
      { key: "region", label: "区域" },
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
    ],
    rows || [],
  );
}

function renderPartnerTierTable(items) {
  renderTable(
    "#partnerTierTable",
    [
      { key: "label", label: "日均单量层级" },
      { key: "partner_count", label: "加盟商数量", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "avg_daily_orders", label: "日均单量", render: formatDecimal, align: "right" },
      { key: "avg_ticket_price", label: "均单价", render: formatMoney, align: "right" },
      { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
      { key: "avg_income_per_order", label: "单均收入", render: formatMoney, align: "right" },
    ],
    items || [],
  );
}

function renderNewPartnerTable(items) {
  renderTable(
    "#newPartnerTable",
    [
      { key: "window_label", label: "表现窗口" },
      { key: "partner_name", label: "合伙人" },
      { key: "open_date", label: "开城时间" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
    ],
    items || [],
    { emptyText: "当前筛选范围暂无新合伙人表现数据" },
  );
}

async function loadPage() {
  const filters = baseFilters();
  const metrics = await api("/api/v1/admin/metrics", filters);
  renderConclusion(metrics);
  renderSummaryCards(metrics);
  renderLineChart("#adminTrendChart", (metrics.daily_trend || []).map((item) => item.date), [
    { name: "总订单", values: (metrics.daily_trend || []).map((item) => item.total_orders) },
    { name: "有效订单", values: (metrics.daily_trend || []).map((item) => item.valid_orders) },
    { name: "完成订单", values: (metrics.daily_trend || []).map((item) => item.completed_orders) },
  ]);
  renderRegionRanking(metrics.region_ranking || []);
  renderPartnerTierTable(metrics.partner_tier_stats || []);
  renderNewPartnerTable(metrics.new_partner_performance || []);
}

function bindEvents() {
  requireElement("#refreshAdmin").addEventListener("click", () => loadPage().catch(showError));
  ["#adminStartDate", "#adminEndDate", "#activeCompletedThreshold", "#rankingLevel", "#partnerTierInput"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  const meta = await api("/api/v1/meta");
  populateFilters(meta);
  bindEvents();
  await loadPage();
}

bootstrap().catch(showError);
