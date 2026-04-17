import {
  api,
  createSearchableSelect,
  renderSystemMeta,
  requireElement,
  setDateRange,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";
import {
  renderCommission,
  renderEntitiesSummary,
  renderEntityContributionCharts,
  renderMerchantIdentity,
  renderMerchantRoster,
  renderRiderRoster,
} from "/static/modules/entities-sections.js";

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

function clearPanels() {
  renderMerchantIdentity([]);
  renderCommission([]);
  renderRiderRoster([]);
  renderMerchantRoster([]);
}

async function loadMerchantIdentity(filters) {
  const result = await api(`/api/v1/partner/${filters.partner_id}/merchant-like-users`, {
    ...filters,
    merchant_like_threshold: merchantLikeThreshold(),
  });
  renderMerchantIdentity(result.items || []);
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
  renderEntitiesSummary(overview);
  renderEntityContributionCharts(newRiders, newMerchants);
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
