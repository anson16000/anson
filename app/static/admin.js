import {
  MAX_QUERY_DAYS,
  api,
  createPageController,
  createPartnerRegionFilterController,
  renderSystemMeta,
  requireElement,
  setDateRange,
  showError,
} from "/static/common.js";
import {
  renderAdminConclusion,
  renderAdminSummaryCards,
  renderAdminTrend,
  renderNewPartnerTable,
  renderPartnerTierTable,
  renderRegionRanking,
} from "/static/modules/admin-sections.js";

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
    filtersController.setPartners(meta.partners || []);
  },
  bindEvents: ({ loadPage, bindRefresh, bindChange }) => {
    bindRefresh("#refreshAdmin");
    bindChange(["#adminStartDate", "#adminEndDate", "#activeCompletedThreshold", "#rankingLevel", "#partnerTierInput"]);
  },
  loadData: async (filters) => {
    const metrics = await api("/api/v1/admin/metrics", filters);
    renderAdminConclusion(metrics);
    renderAdminSummaryCards(metrics);
    renderAdminTrend(metrics);
    renderRegionRanking(metrics.region_ranking || []);
    renderPartnerTierTable(metrics.partner_tier_stats || []);
    renderNewPartnerTable(metrics.new_partner_performance || []);
  },
  onError: showError,
});

controller.bootstrap().catch(showError);
