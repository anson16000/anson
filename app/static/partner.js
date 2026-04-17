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
  renderDirectSpecialSummary,
  renderIssueSummary,
  renderPartnerDailyTrend,
  renderPartnerFinance,
  renderPartnerSummary,
} from "/static/modules/partner-sections.js";

const state = {
  partners: [],
  partnerControl: null,
  partnerId: "",
};

function baseFilters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#partnerStartDate", "#partnerEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    active_completed_threshold: requireElement("#partnerActiveThreshold").value || 1,
    valid_cancel_threshold_minutes: requireElement("#validCancelThreshold").value || 5,
  };
}

function populateFilters(meta) {
  renderSystemMeta(meta, { prefix: "partner" });
  setDateRange("#partnerStartDate", "#partnerEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#partnerSelectControl", {
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
  setHtml("#partnerConclusion", "");
  setHtml("#partnerCards", "");
  setHtml("#directSpecialTags", "");
  setHtml("#directSpecialCards", "");
  setHtml("#issueSummaryTags", "");
  setHtml("#partnerDailyChart", '<div class="empty empty-inline">请选择合伙人后查看城市经营摘要</div>');
  setHtml("#partnerFinanceChart", '<div class="empty empty-inline">请选择合伙人后查看经营收益趋势</div>');
  setHtml("#partnerFinanceTable", '<div class="empty empty-inline">请选择合伙人后查看经营收益明细</div>');
}

async function loadPage() {
  const filters = baseFilters();
  if (!filters.partner_id) {
    clearPanels();
    return;
  }
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
}

function bindEvents() {
  requireElement("#refreshPartner").addEventListener("click", () => loadPage().catch(showError));
  ["#partnerStartDate", "#partnerEndDate", "#partnerActiveThreshold", "#validCancelThreshold"].forEach((selector) => {
    requireElement(selector).addEventListener("change", () => loadPage().catch(showError));
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populateFilters(meta);
  bindEvents();
}

bootstrap().catch(showError);
