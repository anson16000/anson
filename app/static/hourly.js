import {
  api,
  createSearchableSelect,
  renderSystemMeta,
  requireElement,
  setDateRange,
  setHtml,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";
import {
  renderHourlyCharts,
  renderHourlySummary,
} from "/static/modules/hourly-sections.js";

const state = { partners: [], partnerControl: null, partnerId: "" };

function filters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#hourlyStartDate", "#hourlyEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    valid_cancel_threshold_minutes: requireElement("#hourlyValidCancelThreshold").value || 5,
  };
}

function populate(meta) {
  renderSystemMeta(meta, { prefix: "hourly" });
  setDateRange("#hourlyStartDate", "#hourlyEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#hourlyPartnerControl", {
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
  setHtml("#hourlyConclusion", "");
  setHtml("#hourlyCards", "");
  setHtml("#hourlyAcceptedChart", '<div class="empty empty-inline">请选择合伙人后查看时段运力</div>');
  setHtml("#hourlyTable", '<div class="empty empty-inline">请选择合伙人后查看小时运力表</div>');
  setHtml("#hourlyCompletedHeatmap", '<div class="empty empty-inline">请选择合伙人后查看完成订单热力图</div>');
  setHtml("#hourlyCancelledHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消订单热力图</div>');
  setHtml("#hourlyCancelRateHeatmap", '<div class="empty empty-inline">请选择合伙人后查看取消率热力图</div>');
}

async function loadPage() {
  const base = filters();
  if (!base.partner_id) {
    clearPanels();
    return;
  }
  const [overview, hourly] = await Promise.all([
    api(`/api/v1/partner/${base.partner_id}/overview`, base),
    api(`/api/v1/partner/${base.partner_id}/hourly`, base),
  ]);
  renderHourlySummary(overview, hourly);
  renderHourlyCharts(hourly);
}

function bindEvents() {
  requireElement("#refreshHourly").addEventListener("click", () => loadPage().catch(showError));
  ["#hourlyStartDate", "#hourlyEndDate", "#hourlyValidCancelThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populate(meta);
  bindEvents();
}

bootstrap().catch(showError);
