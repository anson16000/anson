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
  renderHourlyCharts,
  renderHourlySummary,
} from "/static/modules/hourly-sections.js";

const PAGE_KEY = "hourly";
const savedFilters = loadFilters(PAGE_KEY);

function exposeValidCancelThreshold() {
  const input = requireElement("#hourlyValidCancelThreshold");
  const field = input.closest(".field");
  const grid = document.querySelector(".toolbar-grid");
  if (field && grid && field.parentElement !== grid) {
    grid.appendChild(field);
  }
  const more = requireElement("#hourlyFilterMore");
  const toggle = requireElement("#hourlyFilterToggle");
  if (more && toggle && more.querySelectorAll(".field").length === 0) {
    more.classList.remove("show");
    more.style.display = "none";
    toggle.style.display = "none";
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
    startDate: "#hourlyStartDate",
    endDate: "#hourlyEndDate",
  },
  maxDays: MAX_QUERY_DAYS,
  requireField: "partner_id",
  additionalFilters: (state) => ({
    partner_id: state.partnerId,
    valid_cancel_threshold_minutes: requireElement("#hourlyValidCancelThreshold").value || 5,
  }),
  clearPanels: () => {
    setHtml("#hourlyConclusion", "");
    setHtml("#hourlyDrillLinks", "");
    setHtml("#hourlyCards .kpi-tier-result", "");
    setHtml("#hourlyCards .kpi-tier-process", "");
    setHtml("#hourlyAcceptedChart", '<div class="empty empty-inline">请选择合伙人后查看时段运力</div>');
    setHtml("#hourlyTable", '<div class="empty empty-inline">请选择合伙人后查看小时运力表</div>');
    setHtml("#hourlyCompletedHeatmap", '<div class="empty empty-inline">请选择合伙人后查看完成订单热力图</div>');
    setHtml("#hourlyCancelledHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消订单热力图</div>');
    setHtml("#hourlyCancelRateHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消率热力图</div>');
  },
  populateFilters: async (meta, state) => {
    exposeValidCancelThreshold();
    renderSystemMeta(meta, { prefix: "hourly" });
    const latestDate = meta.system.latest_data_date;
    setDateRange("#hourlyStartDate", "#hourlyEndDate", latestDate);
    addDateShortcuts("#hourlyStartDate", "#hourlyEndDate", latestDate);
    if (savedFilters.start_date) requireElement("#hourlyStartDate").value = savedFilters.start_date;
    if (savedFilters.end_date) requireElement("#hourlyEndDate").value = savedFilters.end_date;
    state.partners = meta.partners || [];
    if (!state.partnerControl) {
      state.partnerControl = createSearchableSelect("#hourlyPartnerControl", {
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
    if (savedFilters.valid_cancel_threshold_minutes) requireElement("#hourlyValidCancelThreshold").value = savedFilters.valid_cancel_threshold_minutes;
    if (state.partnerId) {
      state.partnerControl.setValue(state.partnerId, false);
      controller.loadPage().catch(showError);
    }
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshHourly");
    bindChange(["#hourlyStartDate", "#hourlyEndDate", "#hourlyValidCancelThreshold"]);
    // 更多筛选折叠
    requireElement("#hourlyFilterToggle").addEventListener("click", () => {
      const toggle = requireElement("#hourlyFilterToggle");
      const more = requireElement("#hourlyFilterMore");
      toggle.classList.toggle("active");
      more.classList.toggle("show");
      toggle.textContent = more.classList.contains("show") ? "收起筛选" : "更多筛选";
    });
  },
  onSaveFilters: (filters) => {
    saveFilters(filters, PAGE_KEY);
    const labelMap = {
      partner_id: "合伙人",
      valid_cancel_threshold_minutes: "有效取消阈值",
    };
    renderFilterSummary("#hourlyFilterSummary", filters, labelMap);
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
    const [overview, hourly] = await Promise.all([
      api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
      api(`/api/v1/partner/${filters.partner_id}/hourly`, filters),
    ]);
    renderHourlySummary(overview, hourly);
    renderHourlyCharts(hourly);
    initHeatmapTabs();
  },
  onError: showError,
});

controller.bootstrap().catch(showError);

function initHeatmapTabs() {
  const tabContainer = document.querySelector(".heatmap-tabs");
  if (!tabContainer) return;
  tabContainer.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      tabContainer.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.tab === tab);
      });
    });
  });
}
