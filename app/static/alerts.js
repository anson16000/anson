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
  saveFilters,
  setDateRange,
  showError,
} from "/static/common.js";
import { renderAlertsSummary, renderAlertsTables } from "/static/modules/alerts-sections.js";

const PAGE_KEY = "alerts";
const savedFilters = loadFilters(PAGE_KEY);

const sharedData = loadFilters("");
const urlParams = new URLSearchParams(window.location.search);
const urlPartnerId = urlParams.get("partner_id") || "";
const urlCity = urlParams.get("city") || "";
const urlStartDate = urlParams.get("start_date") || "";
const urlEndDate = urlParams.get("end_date") || "";
if (urlPartnerId) savedFilters.partner_id = urlPartnerId;
else if (sharedData._shared_partner_id) savedFilters.partner_id = sharedData._shared_partner_id;
if (urlCity) savedFilters.city = urlCity;
else if (sharedData._shared_city) savedFilters.city = sharedData._shared_city;
if (urlStartDate) savedFilters.start_date = urlStartDate;
else if (sharedData._shared_start_date) savedFilters.start_date = sharedData._shared_start_date;
if (urlEndDate) savedFilters.end_date = urlEndDate;
else if (sharedData._shared_end_date) savedFilters.end_date = sharedData._shared_end_date;

if (!urlPartnerId && !urlCity && !urlStartDate && !urlEndDate) {
  try {
    const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
    delete data._shared_partner_id;
    delete data._shared_city;
    delete data._shared_start_date;
    delete data._shared_end_date;
    sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
  } catch (_) {
    // ignore storage failures
  }
}

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
    const latestDate = meta.system.latest_data_date;
    setDateRange("#alertsStartDate", "#alertsEndDate", latestDate);
    addDateShortcuts("#alertsStartDate", "#alertsEndDate", latestDate);

    if (savedFilters.start_date) requireElement("#alertsStartDate").value = savedFilters.start_date;
    if (savedFilters.end_date) requireElement("#alertsEndDate").value = savedFilters.end_date;

    filtersController.setPartners(meta.partners || []);
    if (savedFilters.province) filtersController.filters.province = savedFilters.province;
    if (savedFilters.city) filtersController.filters.city = savedFilters.city;
    if (savedFilters.district) filtersController.filters.district = savedFilters.district;
    if (savedFilters.partner_id) filtersController.filters.partner_id = savedFilters.partner_id;
    filtersController.render();

    if (savedFilters.active_completed_threshold) {
      requireElement("#alertsActiveThreshold").value = savedFilters.active_completed_threshold;
    }
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshAlerts");
    bindChange(["#alertsStartDate", "#alertsEndDate", "#alertsActiveThreshold"]);
    requireElement("#alertsFilterToggle").addEventListener("click", () => {
      const toggle = requireElement("#alertsFilterToggle");
      const more = requireElement("#alertsFilterMore");
      toggle.classList.toggle("active");
      more.classList.toggle("show");
      toggle.textContent = more.classList.contains("show") ? "收起筛选" : "更多筛选";
    });
  },
  onSaveFilters: (filters) => {
    saveFilters(filters, PAGE_KEY);
    const labelMap = {
      province: "省份",
      city: "城市",
      district: "区县",
      partner_id: "合伙人",
      active_completed_threshold: "活跃完成单阈值",
    };
    renderFilterSummary("#alertsFilterSummary", filters, labelMap);
    try {
      const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
      if (filters.partner_id) data._shared_partner_id = filters.partner_id;
      if (filters.city) data._shared_city = filters.city;
      if (filters.start_date) data._shared_start_date = filters.start_date;
      if (filters.end_date) data._shared_end_date = filters.end_date;
      sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
    } catch (_) {
      // ignore storage failures
    }
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
