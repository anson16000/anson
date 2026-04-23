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
  setHtml,
  showError,
} from "/static/common.js";
import {
  renderDirectSpecialSummary,
  renderIssueSummary,
  renderPartnerDailyTrend,
  renderPartnerFinance,
  renderPartnerSummary,
} from "/static/modules/partner-sections.js";

const PAGE_KEY = "partner";
const savedFilters = loadFilters(PAGE_KEY);

function exposeValidCancelThreshold() {
  const input = requireElement("#validCancelThreshold");
  const field = input.closest(".field");
  const grid = document.querySelector(".toolbar-grid");
  if (field && grid && field.parentElement !== grid) {
    grid.appendChild(field);
  }
}

// Check for cross-page shared partner_id, city, dates or URL params
const sharedData = loadFilters("");
const urlPartnerId = new URLSearchParams(window.location.search).get("partner_id") || "";
const urlStartDate = new URLSearchParams(window.location.search).get("start_date") || "";
const urlEndDate = new URLSearchParams(window.location.search).get("end_date") || "";
const sharedPartnerId = urlPartnerId || sharedData._shared_partner_id || "";
if (sharedPartnerId) savedFilters.partner_id = sharedPartnerId;
if (urlStartDate) savedFilters.start_date = urlStartDate;
else if (sharedData._shared_start_date) savedFilters.start_date = sharedData._shared_start_date;
if (urlEndDate) savedFilters.end_date = urlEndDate;
else if (sharedData._shared_end_date) savedFilters.end_date = sharedData._shared_end_date;
if (sharedData._shared_valid_cancel_threshold_minutes) {
  savedFilters.valid_cancel_threshold_minutes = sharedData._shared_valid_cancel_threshold_minutes;
}
// Clean up shared keys after reading (only if not from URL)
if (!urlPartnerId && !urlStartDate && !urlEndDate) {
  try {
    const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
    delete data._shared_partner_id;
    delete data._shared_start_date;
    delete data._shared_end_date;
    sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
  } catch (_) {}
}

const controller = createPageController({
  initialState: {
    partners: [],
    partnerControl: null,
    partnerId: savedFilters.partner_id || "",
  },
  selectors: {
    startDate: "#partnerStartDate",
    endDate: "#partnerEndDate",
  },
  maxDays: MAX_QUERY_DAYS,
  requireField: "partner_id",
  additionalFilters: (state) => ({
    partner_id: state.partnerId,
    active_completed_threshold: requireElement("#partnerActiveThreshold").value || 1,
    valid_cancel_threshold_minutes: requireElement("#validCancelThreshold").value || 5,
  }),
  clearPanels: () => {
    setHtml("#partnerConclusion", "");
    setHtml("#partnerCards .kpi-tier-result", "");
    setHtml("#partnerCards .kpi-tier-process", "");
    setHtml("#partnerCards .kpi-tier-action", "");
    setHtml("#directSpecialTags", "");
    setHtml("#directSpecialCards", "");
    setHtml("#issueSummaryTags", "");
    setHtml("#partnerDrillLinks", "");
    setHtml("#partnerDailyChart", '<div class="empty empty-inline">请选择合伙人后查看城市经营趋势</div>');
    setHtml("#partnerFinanceChart", '<div class="empty empty-inline">请选择合伙人后查看经营收益趋势</div>');
    setHtml("#partnerFinanceTable", '<div class="empty empty-inline">请选择合伙人后查看经营收益明细</div>');
  },
  populateFilters: async (meta, state) => {
    exposeValidCancelThreshold();
    renderSystemMeta(meta, { prefix: "partner" });
    const latestDate = meta.system.latest_data_date;
    setDateRange("#partnerStartDate", "#partnerEndDate", latestDate);
    addDateShortcuts("#partnerStartDate", "#partnerEndDate", latestDate);
    // Restore shared date filters
    if (savedFilters.start_date) requireElement("#partnerStartDate").value = savedFilters.start_date;
    if (savedFilters.end_date) requireElement("#partnerEndDate").value = savedFilters.end_date;
    state.partners = meta.partners || [];
    if (!state.partnerControl) {
      state.partnerControl = createSearchableSelect("#partnerSelectControl", {
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
    // 恢复保存的筛选条件
    if (savedFilters.active_completed_threshold) requireElement("#partnerActiveThreshold").value = savedFilters.active_completed_threshold;
    if (savedFilters.valid_cancel_threshold_minutes) requireElement("#validCancelThreshold").value = savedFilters.valid_cancel_threshold_minutes;
    if (state.partnerId) {
      state.partnerControl.setValue(state.partnerId, false);
      controller.loadPage().catch(showError);
    }
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshPartner");
    bindChange(["#partnerStartDate", "#partnerEndDate", "#partnerActiveThreshold", "#validCancelThreshold"]);
    // 更多筛选折叠
    requireElement("#partnerFilterToggle").addEventListener("click", () => {
      const toggle = requireElement("#partnerFilterToggle");
      const more = requireElement("#partnerFilterMore");
      toggle.classList.toggle("active");
      more.classList.toggle("show");
      toggle.textContent = more.classList.contains("show") ? "收起筛选" : "更多筛选";
    });
  },
  onSaveFilters: (filters) => {
    saveFilters(filters, PAGE_KEY);
    const labelMap = {
      partner_id: "合伙人",
      active_completed_threshold: "活跃完成单阈值",
      valid_cancel_threshold_minutes: "有效取消阈值",
    };
    renderFilterSummary("#partnerFilterSummary", filters, labelMap);
    // Save partner_id and dates to shared state for cross-page navigation
    try {
      const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
      if (filters.partner_id) data._shared_partner_id = filters.partner_id;
      if (filters.start_date) data._shared_start_date = filters.start_date;
      if (filters.end_date) data._shared_end_date = filters.end_date;
      if (filters.valid_cancel_threshold_minutes) data._shared_valid_cancel_threshold_minutes = filters.valid_cancel_threshold_minutes;
      sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
    } catch (_) {}
  },
  loadData: async (filters) => {
    const [overview, daily, directData] = await Promise.all([
      api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
      api(`/api/v1/partner/${filters.partner_id}/daily`, filters),
      api("/api/v1/direct/cancel-daily", filters),
    ]);
    renderPartnerSummary(overview);
    renderPartnerDailyTrend(daily);
    renderPartnerFinance(daily);
    renderDirectSpecialSummary(directData);
    renderIssueSummary(overview, directData);
    if (new URLSearchParams(window.location.search).get("section") === "direct") {
      document.getElementById("directSpecialSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  },
  onError: showError,
});

controller.bootstrap().catch(showError);
