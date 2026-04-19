import {
  MAX_QUERY_DAYS,
  api,
  createPageController,
  createSearchableSelect,
  renderSystemMeta,
  requireElement,
  setDateRange,
  showError,
} from "/static/common.js";
import {
  renderCommission,
  renderEntitiesSummary,
  renderEntityContributionCharts,
  renderMerchantIdentity,
  renderMerchantRoster,
  renderRiderRoster,
} from "/static/modules/entities-sections.js";

const controller = createPageController({
  initialState: {
    partners: [],
    partnerControl: null,
    partnerId: "",
  },
  selectors: {
    startDate: "#entitiesStartDate",
    endDate: "#entitiesEndDate",
  },
  maxDays: MAX_QUERY_DAYS,
  requireField: "partner_id",
  additionalFilters: (state) => ({
    partner_id: state.partnerId,
    active_completed_threshold: requireElement("#entitiesActiveThreshold").value || 1,
  }),
  clearPanels: () => {
    renderMerchantIdentity([]);
    renderCommission([]);
    renderRiderRoster([]);
    renderMerchantRoster([]);
  },
  populateFilters: async (meta, state) => {
    renderSystemMeta(meta, { prefix: "entities" });
    setDateRange("#entitiesStartDate", "#entitiesEndDate", meta.system.latest_data_date);
    state.partners = meta.partners || [];
    if (!state.partnerControl) {
      state.partnerControl = createSearchableSelect("#entitiesPartnerControl", {
        placeholder: "输入合伙人名称或 ID 搜索",
        allLabel: "请选择",
        onChange: (value) => {
          state.partnerId = value;
          controller.loadPage().catch(showError);
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
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshEntities");
    bindChange(["#entitiesStartDate", "#entitiesEndDate", "#entitiesActiveThreshold"]);
    requireElement("#merchantLikeThresholdLocal").addEventListener("change", () => {
      const filters = controller.getBaseFilters();
      if (!filters.partner_id) return;
      loadMerchantIdentity(filters).catch(showError);
    });
    requireElement("#entitiesRiderListFilter").addEventListener("change", () => {
      const filters = controller.getBaseFilters();
      if (!filters.partner_id) return;
      loadRosters(filters).catch(showError);
    });
    requireElement("#entitiesMerchantListFilter").addEventListener("change", () => {
      const filters = controller.getBaseFilters();
      if (!filters.partner_id) return;
      loadRosters(filters).catch(showError);
    });
  },
  loadData: async (filters) => {
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
  },
  onError: showError,
});

function riderListFlag() {
  return requireElement("#entitiesRiderListFilter").value || "all";
}

function merchantListFlag() {
  return requireElement("#entitiesMerchantListFilter").value || "all";
}

function merchantLikeThreshold() {
  return requireElement("#merchantLikeThresholdLocal").value || 20;
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

controller.bootstrap().catch(showError);
