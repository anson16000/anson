import {
  MAX_QUERY_DAYS,
  addDateShortcuts,
  api,
  createPageController,
  createSearchableSelect,
  loadFilters,
  renderFilterSummary,
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
  renderOrderSourceSummary,
  renderOrderSourceTable,
  renderRiderRoster,
} from "/static/modules/entities-sections.js";

const PAGE_KEY = "entities";
const savedFilters = loadFilters(PAGE_KEY);

const sharedData = loadFilters("");
const urlParams = new URLSearchParams(window.location.search);
const sharedPartnerId = urlParams.get("partner_id") || sharedData._shared_partner_id || "";
if (sharedPartnerId) savedFilters.partner_id = sharedPartnerId;

const sharedStartDate = urlParams.get("start_date") || sharedData._shared_start_date || "";
if (sharedStartDate) savedFilters.start_date = sharedStartDate;

const sharedEndDate = urlParams.get("end_date") || sharedData._shared_end_date || "";
if (sharedEndDate) savedFilters.end_date = sharedEndDate;

if (!urlParams.get("partner_id") && !urlParams.get("start_date") && !urlParams.get("end_date")) {
  try {
    const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
    delete data._shared_partner_id;
    delete data._shared_start_date;
    delete data._shared_end_date;
    sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
  } catch (_) {
    // ignore session storage issues
  }
}

const controller = createPageController({
  initialState: {
    partners: [],
    partnerControl: null,
    partnerId: savedFilters.partner_id || "",
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
    renderOrderSourceSummary({ items: [] });
    renderOrderSourceTable([]);
  },
  populateFilters: async (meta, state) => {
    renderSystemMeta(meta, { prefix: "entities" });
    const latestDate = meta.system.latest_data_date;
    setDateRange("#entitiesStartDate", "#entitiesEndDate", latestDate);
    addDateShortcuts("#entitiesStartDate", "#entitiesEndDate", latestDate);
    if (savedFilters.start_date) requireElement("#entitiesStartDate").value = savedFilters.start_date;
    if (savedFilters.end_date) requireElement("#entitiesEndDate").value = savedFilters.end_date;
    if (savedFilters.active_completed_threshold) {
      requireElement("#entitiesActiveThreshold").value = savedFilters.active_completed_threshold;
    }

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

    if (state.partnerId) {
      state.partnerControl.setValue(state.partnerId, false);
      controller.loadPage().catch(showError);
    }
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshEntities");
    bindChange(["#entitiesStartDate", "#entitiesEndDate", "#entitiesActiveThreshold"]);

    requireElement("#entitiesFilterToggle").addEventListener("click", () => {
      const toggle = requireElement("#entitiesFilterToggle");
      const more = requireElement("#entitiesFilterMore");
      toggle.classList.toggle("active");
      more.classList.toggle("show");
      toggle.textContent = more.classList.contains("show") ? "收起筛选" : "更多筛选";
    });

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
  onSaveFilters: (filters) => {
    const labelMap = {
      partner_id: "合伙人",
      active_completed_threshold: "活跃完成单阈值",
    };
    renderFilterSummary("#entitiesFilterSummary", filters, labelMap);
    try {
      const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
      if (filters.partner_id) data._shared_partner_id = filters.partner_id;
      if (filters.start_date) data._shared_start_date = filters.start_date;
      if (filters.end_date) data._shared_end_date = filters.end_date;
      sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
    } catch (_) {
      // ignore session storage issues
    }
  },
  loadData: async (filters) => {
    const [overview, newRiders, newMerchants, riderIncome, orderSources] = await Promise.all([
      api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
      api(`/api/v1/partner/${filters.partner_id}/new-riders`, filters),
      api(`/api/v1/partner/${filters.partner_id}/new-merchants`, filters),
      api(`/api/v1/partner/${filters.partner_id}/income/riders`, filters),
      api(`/api/v1/partner/${filters.partner_id}/order-sources`, {
        start_date: filters.start_date,
        end_date: filters.end_date,
      }),
    ]);

    renderEntitiesSummary(overview);
    await Promise.all([loadRosters(filters), loadMerchantIdentity(filters)]);
    renderCommission(riderIncome.items || []);
    renderOrderSourceSummary(orderSources);
    renderOrderSourceTable(orderSources.items || []);
    renderEntityContributionCharts(newRiders, newMerchants);
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
    start_date: filters.start_date,
    end_date: filters.end_date,
    merchant_like_threshold: merchantLikeThreshold(),
  });
  renderMerchantIdentity(result.items || []);
}

async function loadRosters(filters) {
  const [riders, merchants] = await Promise.all([
    api(`/api/v1/partner/${filters.partner_id}/riders`, {
      start_date: filters.start_date,
      end_date: filters.end_date,
      new_flag: riderListFlag(),
    }),
    api(`/api/v1/partner/${filters.partner_id}/merchants`, {
      start_date: filters.start_date,
      end_date: filters.end_date,
      new_flag: merchantListFlag(),
    }),
  ]);
  renderRiderRoster(riders.items || []);
  renderMerchantRoster(merchants.items || []);
}

controller.bootstrap().catch(showError);
