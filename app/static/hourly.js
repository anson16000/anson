import {
  MAX_QUERY_DAYS,
  api,
  createPageController,
  createSearchableSelect,
  renderSystemMeta,
  requireElement,
  setDateRange,
  setHtml,
  showError,
} from "/static/common.js";
import {
  renderHourlyCharts,
  renderHourlySummary,
} from "/static/modules/hourly-sections.js";

const controller = createPageController({
  initialState: {
    partners: [],
    partnerControl: null,
    partnerId: "",
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
    setHtml("#hourlyCards", "");
    setHtml("#hourlyAcceptedChart", '<div class="empty empty-inline">请选择合伙人后查看时段运力</div>');
    setHtml("#hourlyTable", '<div class="empty empty-inline">请选择合伙人后查看小时运力表</div>');
    setHtml("#hourlyCompletedHeatmap", '<div class="empty empty-inline">请选择合伙人后查看完成订单热力图</div>');
    setHtml("#hourlyCancelledHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消订单热力图</div>');
    setHtml("#hourlyCancelRateHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消率热力图</div>');
  },
  populateFilters: async (meta, state) => {
    renderSystemMeta(meta, { prefix: "hourly" });
    setDateRange("#hourlyStartDate", "#hourlyEndDate", meta.system.latest_data_date);
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
  },
  bindEvents: ({ bindRefresh, bindChange }) => {
    bindRefresh("#refreshHourly");
    bindChange(["#hourlyStartDate", "#hourlyEndDate", "#hourlyValidCancelThreshold"]);
  },
  loadData: async (filters) => {
    const [overview, hourly] = await Promise.all([
      api(`/api/v1/partner/${filters.partner_id}/overview`, filters),
      api(`/api/v1/partner/${filters.partner_id}/hourly`, filters),
    ]);
    renderHourlySummary(overview, hourly);
    renderHourlyCharts(hourly);
  },
  onError: showError,
});

controller.bootstrap().catch(showError);
