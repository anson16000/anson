import {
  api,
  createPartnerRegionFilterController,
  renderSystemMeta,
  requireElement,
  setDateRange,
  showError,
  validateDateRangeBySelectors,
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

async function loadPage() {
  const current = filters();
  const [metrics, health, fluctuation] = await Promise.all([
    api("/api/v1/admin/metrics", current),
    api("/api/v1/admin/health", current),
    api("/api/v1/admin/partners/fluctuation", { start_date: current.start_date, end_date: current.end_date }),
  ]);
  renderAlertsSummary(metrics, health);
  renderAlertsTables(metrics, health, fluctuation);
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
