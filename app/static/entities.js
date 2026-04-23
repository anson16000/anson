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
  saveFilters,
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
  renderRiderTierTable,
} from "/static/modules/entities-sections.js";

const PAGE_KEY = "entities";
const DEFAULT_VALID_CANCEL_THRESHOLD = "5";
const DEFAULT_RIDER_TIERS = "1-9,10-29,30-49,50+";
const DEFAULT_RIDER_TARGET_COMPLETED = "10";
const DEFAULT_RIDER_TARGET_DAYS = "10";
const savedFilters = loadFilters(PAGE_KEY);
const sharedData = loadFilters("");
const urlParams = new URLSearchParams(window.location.search);

const sharedPartnerId = urlParams.get("partner_id") || sharedData._shared_partner_id || "";
if (sharedPartnerId) savedFilters.partner_id = sharedPartnerId;

const sharedStartDate = urlParams.get("start_date") || sharedData._shared_start_date || "";
if (sharedStartDate) savedFilters.start_date = sharedStartDate;

const sharedEndDate = urlParams.get("end_date") || sharedData._shared_end_date || "";
if (sharedEndDate) savedFilters.end_date = sharedEndDate;

if (sharedData._shared_valid_cancel_threshold_minutes) {
  savedFilters.valid_cancel_threshold_minutes = sharedData._shared_valid_cancel_threshold_minutes;
}

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

function ensureVisibleValidCancelThresholdField() {
  if (document.querySelector("#entitiesValidCancelThreshold")) return;
  const grid = document.querySelector(".toolbar-grid");
  if (!grid) return;
  const label = document.createElement("label");
  label.className = "field";
  label.innerHTML = '<span>有效取消阈值（分钟）</span><input id="entitiesValidCancelThreshold" type="number" min="1" value="5">';
  grid.appendChild(label);
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

function riderTargetCompletedOrders() {
  return requireElement("#entitiesRiderTargetCompleted").value || DEFAULT_RIDER_TARGET_COMPLETED;
}

function riderTargetCompletedDays() {
  return requireElement("#entitiesRiderTargetDays").value || DEFAULT_RIDER_TARGET_DAYS;
}

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

function buildRiderTierPayload() {
  const tiers = parseTierText(requireElement("#entitiesRiderTierInput").value);
  return tiers.length ? JSON.stringify(tiers) : "";
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
      rider_tiers: buildRiderTierPayload(),
      target_daily_completed_orders: riderTargetCompletedOrders(),
      target_completed_days: riderTargetCompletedDays(),
    }),
    api(`/api/v1/partner/${filters.partner_id}/merchants`, {
      start_date: filters.start_date,
      end_date: filters.end_date,
      new_flag: merchantListFlag(),
    }),
  ]);
  renderRiderRoster(riders.items || [], riders.date_columns || []);
  renderRiderTierTable(riders.rider_tiers || []);
  renderMerchantRoster(merchants.items || []);
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
    valid_cancel_threshold_minutes: requireElement("#entitiesValidCancelThreshold").value || DEFAULT_VALID_CANCEL_THRESHOLD,
    rider_tiers: buildRiderTierPayload(),
    rider_target_completed_orders: riderTargetCompletedOrders(),
    rider_target_completed_days: riderTargetCompletedDays(),
  }),
  clearPanels: () => {
    renderMerchantIdentity([]);
    renderCommission([]);
    renderRiderRoster([], []);
    renderRiderTierTable([]);
    renderMerchantRoster([]);
    renderOrderSourceSummary({ items: [] });
    renderOrderSourceTable([]);
  },
  populateFilters: async (meta, state) => {
    ensureVisibleValidCancelThresholdField();
    renderSystemMeta(meta, { prefix: "entities" });
    const latestDate = meta.system.latest_data_date;
    setDateRange("#entitiesStartDate", "#entitiesEndDate", latestDate);
    addDateShortcuts("#entitiesStartDate", "#entitiesEndDate", latestDate);

    if (savedFilters.start_date) requireElement("#entitiesStartDate").value = savedFilters.start_date;
    if (savedFilters.end_date) requireElement("#entitiesEndDate").value = savedFilters.end_date;
    if (savedFilters.active_completed_threshold) {
      requireElement("#entitiesActiveThreshold").value = savedFilters.active_completed_threshold;
    }
    requireElement("#entitiesValidCancelThreshold").value =
      savedFilters.valid_cancel_threshold_minutes || DEFAULT_VALID_CANCEL_THRESHOLD;
    requireElement("#entitiesRiderTierInput").value = savedFilters.rider_tiers || DEFAULT_RIDER_TIERS;
    requireElement("#entitiesRiderTargetCompleted").value =
      savedFilters.rider_target_completed_orders || DEFAULT_RIDER_TARGET_COMPLETED;
    requireElement("#entitiesRiderTargetDays").value =
      savedFilters.rider_target_completed_days || DEFAULT_RIDER_TARGET_DAYS;

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
    bindChange([
      "#entitiesStartDate",
      "#entitiesEndDate",
      "#entitiesActiveThreshold",
      "#entitiesValidCancelThreshold",
      "#entitiesRiderTierInput",
    ]);

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

    requireElement("#entitiesRiderTargetCompleted").addEventListener("change", () => {
      const filters = controller.getBaseFilters();
      saveFilters({ ...loadFilters(PAGE_KEY), rider_target_completed_orders: riderTargetCompletedOrders() }, PAGE_KEY);
      if (!filters.partner_id) return;
      loadRosters(filters).catch(showError);
    });

    requireElement("#entitiesRiderTargetDays").addEventListener("change", () => {
      const filters = controller.getBaseFilters();
      saveFilters({ ...loadFilters(PAGE_KEY), rider_target_completed_days: riderTargetCompletedDays() }, PAGE_KEY);
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
    saveFilters(filters, PAGE_KEY);
    renderFilterSummary("#entitiesFilterSummary", filters, {
      partner_id: "合伙人",
      active_completed_threshold: "活跃完成单阈值",
      valid_cancel_threshold_minutes: "有效取消阈值",
      rider_tiers: "骑手单量分层",
      rider_target_completed_orders: "达标要求单量",
    });
    try {
      const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
      if (filters.partner_id) data._shared_partner_id = filters.partner_id;
      if (filters.start_date) data._shared_start_date = filters.start_date;
      if (filters.end_date) data._shared_end_date = filters.end_date;
      if (filters.valid_cancel_threshold_minutes) {
        data._shared_valid_cancel_threshold_minutes = filters.valid_cancel_threshold_minutes;
      }
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

controller.bootstrap().catch(showError);
