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
  renderAlertsSummary,
  renderAlertsTables,
} from "/static/modules/alerts-sections.js";

const filtersController = createPartnerRegionFilterController({
  selectors: {
    province: "#alertsProvinceControl",
    city: "#alertsCityControl",
    district: "#alertsDistrictControl",
    partner_id: "#alertsPartnerControl",
  },
  onChange: () => controller.loadPage().catch(showError),
});

const controller = createPageController({
  selectors: {
    startDate: "#alertsStartDate",
    endDate: "#alertsEndDate",
  },
  maxDays: MAX_QUERY_DAYS,
  additionalFilters: () => ({
    province: filtersController.filters.province,
    city: filtersController.filters.city,
    district: filtersController.filters.district,
    partner_id: filtersController.filters.partner_id,
    active_completed_threshold: requireElement("#alertsActiveThreshold").value || 1,
  }),
  populateFilters: async (meta) => {
    renderSystemMeta(meta, { prefix: "alerts" });
    setDateRange("#alertsStartDate", "#alertsEndDate", meta.system.latest_data_date);
    filtersController.setPartners(meta.partners || []);
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshAlerts");
    bindChange(["#alertsStartDate", "#alertsEndDate", "#alertsActiveThreshold"]);
  },
  loadData: async (filters) => {
    const [metrics, health, fluctuation] = await Promise.all([
      api("/api/v1/admin/metrics", filters),
      api("/api/v1/admin/health", filters),
      api("/api/v1/admin/partners/fluctuation", filters),
    ]);
    renderAlertsSummary(metrics, health);
    renderAlertsTables(metrics, health, fluctuation);
  },
  onError: showError,
});

controller.bootstrap().catch(showError);
