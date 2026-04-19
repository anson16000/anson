import {
  MAX_QUERY_DAYS,
  addDateShortcuts,
  api,
  createPageController,
  createPartnerRegionFilterController,
  loadFilters,
  renderFilterSummary,
  renderSystemMeta,
  requireElement,
  setDateRange,
  showError,
} from "/static/common.js";
import {
  renderAdminConclusion,
  renderAdminSummaryCards,
  renderAdminTrend,
  renderAnomalySummary,
  renderNewPartnerTable,
  renderPartnerDailyComparison,
  renderPartnerTierTable,
  renderRegionRanking,
} from "/static/modules/admin-sections.js";

const PAGE_KEY = "admin";
const savedFilters = loadFilters(PAGE_KEY);

const filtersController = createPartnerRegionFilterController({
  selectors: {
    province: "#adminProvinceControl",
    city: "#adminCityControl",
    district: "#adminDistrictControl",
    partner_id: "#adminPartnerControl",
  },
  onChange: () => controller.loadPage().catch(showError),
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

const controller = createPageController({
  selectors: {
    startDate: "#adminStartDate",
    endDate: "#adminEndDate",
  },
  maxDays: MAX_QUERY_DAYS,
  additionalFilters: () => {
    const tiers = parseTierText(requireElement("#partnerTierInput").value);
    return {
      province: filtersController.filters.province,
      city: filtersController.filters.city,
      district: filtersController.filters.district,
      partner_id: filtersController.filters.partner_id,
      active_completed_threshold: requireElement("#activeCompletedThreshold").value || 1,
      ranking_level: requireElement("#rankingLevel").value || "all",
      partner_tiers: tiers.length ? JSON.stringify(tiers) : "",
    };
  },
  populateFilters: async (meta) => {
    renderSystemMeta(meta, { prefix: "admin" });
    setDateRange("#adminStartDate", "#adminEndDate", meta.system.latest_data_date);
    addDateShortcuts("#adminStartDate", "#adminEndDate", meta.system.latest_data_date);
    filtersController.setPartners(meta.partners || []);
    // 恢复保存的筛选条件
    if (savedFilters.province) filtersController.filters.province = savedFilters.province;
    if (savedFilters.city) filtersController.filters.city = savedFilters.city;
    if (savedFilters.district) filtersController.filters.district = savedFilters.district;
    if (savedFilters.partner_id) filtersController.filters.partner_id = savedFilters.partner_id;
    filtersController.render();
    if (savedFilters.active_completed_threshold) requireElement("#activeCompletedThreshold").value = savedFilters.active_completed_threshold;
    if (savedFilters.ranking_level) requireElement("#rankingLevel").value = savedFilters.ranking_level;
    if (savedFilters.partner_tiers) requireElement("#partnerTierInput").value = savedFilters.partner_tiers;
  },
  bindEvents: ({ loadPage, bindRefresh, bindChange }) => {
    bindRefresh("#refreshAdmin");
    bindChange(["#adminStartDate", "#adminEndDate", "#activeCompletedThreshold", "#rankingLevel", "#partnerTierInput"]);
    // 更多筛选折叠
    requireElement("#adminFilterToggle").addEventListener("click", () => {
      const toggle = requireElement("#adminFilterToggle");
      const more = requireElement("#adminFilterMore");
      toggle.classList.toggle("active");
      more.classList.toggle("show");
      toggle.textContent = more.classList.contains("show") ? "收起筛选" : "更多筛选";
    });
  },
  onSaveFilters: (filters) => {
    const labelMap = {
      province: "省份",
      city: "城市",
      district: "区县",
      partner_id: "合伙人",
      active_completed_threshold: "活跃完成单阈值",
      ranking_level: "区域排名维度",
    };
    renderFilterSummary("#adminFilterSummary", filters, labelMap);
    // Save shared state for cross-page navigation
    try {
      const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
      if (filters.partner_id) data._shared_partner_id = filters.partner_id;
      if (filters.city) data._shared_city = filters.city;
      if (filters.start_date) data._shared_start_date = filters.start_date;
      if (filters.end_date) data._shared_end_date = filters.end_date;
      sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
    } catch (_) {}
  },
  loadData: async (filters) => {
    const metrics = await api("/api/v1/admin/metrics", filters);
    renderAdminConclusion(metrics);
    renderAdminSummaryCards(metrics);
    renderAnomalySummary(metrics);
    renderAdminTrend(metrics);
    renderRegionRanking(metrics.region_ranking || []);
    renderPartnerTierTable(metrics.partner_tier_stats || []);
    renderPartnerDailyComparison(metrics.partner_recent_daily || []);
    const allNewPartners = metrics.new_partner_performance || [];
    renderNewPartnerTable(allNewPartners.filter((item) => item.window_label === "30日表现"), "#newPartnerTable30", "30日暂无数据");
    renderNewPartnerTable(allNewPartners.filter((item) => item.window_label === "60日表现"), "#newPartnerTable60", "60日暂无数据");
    renderNewPartnerTable(allNewPartners.filter((item) => item.window_label === "90日表现"), "#newPartnerTable90", "90日暂无数据");
  },
  onError: showError,
});

controller.bootstrap().catch(showError);
