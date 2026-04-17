import {
  api,
  createSearchableSelect,
  formatDecimal,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderLineChart,
  renderSystemMeta,
  renderTable,
  renderTags,
  requireElement,
  setDateRange,
  setHtml,
  showError,
  validateDateRangeBySelectors,
} from "/static/common.js";

const state = {
  partners: [],
  partnerControl: null,
  partnerId: "",
};

function directFilters() {
  const { startDateText, endDateText } = validateDateRangeBySelectors("#directStartDate", "#directEndDate", 31);
  return {
    partner_id: state.partnerId,
    start_date: startDateText,
    end_date: endDateText,
    active_completed_threshold: requireElement("#directActiveThreshold", "活跃完成单阈值").value || 1,
    valid_cancel_threshold_minutes: requireElement("#directValidCancelThreshold", "有效取消阈值").value || 5,
  };
}

function populateFilters(meta) {
  renderSystemMeta(meta, { prefix: "direct" });
  setDateRange("#directStartDate", "#directEndDate", meta.system.latest_data_date);
  state.partners = meta.partners || [];
  if (!state.partnerControl) {
    state.partnerControl = createSearchableSelect("#directPartnerControl", {
      placeholder: "输入合伙人名称或 ID 搜索",
      allLabel: "请选择",
      onChange: (value) => {
        state.partnerId = value;
        runPage().catch(showError);
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
  state.partnerControl.setValue(state.partnerId, false);
}

function clearPanels() {
  renderTags("#directConclusion", []);
  renderCards("#directCards", []);
  renderCards("#directRevenueCards", []);
  setHtml("#directDayChart", '<div class="empty empty-inline">请选择合伙人后查看日单量统计</div>');
  setHtml("#directEffectiveChart", '<div class="empty empty-inline">请选择合伙人后查看有效订单统计</div>');
  renderTable("#directCancelTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看日单量统计" });
  renderTable("#directEffectiveTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看有效订单统计" });
  renderTable("#directHourlyTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看时间段数据" });
  renderTable("#directSourceTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看渠道对比" });
  renderTable("#directCouponTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看优惠金额统计" });
  renderTable("#directRiderCommissionTable", [{ key: "message", label: "提示" }], [], { emptyText: "请选择合伙人后查看收益指标" });
}

function appendTotalRow(items, numericKeys, labelKey = "label") {
  if (!items.length) return items;
  const total = { [labelKey]: "合计", order_source: "合计", date: "合计", hour: "合计" };
  numericKeys.forEach((key) => {
    total[key] = items.reduce((sum, item) => sum + Number(item[key] || 0), 0);
  });
  return [...items, total];
}

function safeEfficiency(completedOrders, acceptedRiders) {
  return Number(acceptedRiders || 0) > 0 ? Number(completedOrders || 0) / Number(acceptedRiders || 0) : 0;
}

function renderConclusion(summary) {
  const tags = [];
  if ((summary.cancel_rate || 0) >= 0.2) tags.push("取消率偏高，直营页建议优先检查履约和调度");
  else tags.push("取消率整体可控");
  if ((summary.valid_cancel_rate || 0) >= 0.08) tags.push("有效订单取消率偏高，建议排查超时与接单后取消");
  else tags.push("有效订单取消率整体稳定");
  if ((summary.sla_on_time_rate || 0) < 0.8) tags.push(`SLA 履约率偏低，当前按 ${summary.sla_minutes || 30} 分钟口径计算`);
  else tags.push(`SLA 履约率稳定，当前按 ${summary.sla_minutes || 30} 分钟口径计算`);
  renderTags("#directConclusion", tags);
}

function renderSummaryCards(summary) {
  renderCards("#directCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "完成率", value: formatPercent(summary.completion_rate) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
    { label: "总部补贴", value: formatMoney(summary.hq_subsidy_total) },
    { label: "合伙人补贴", value: formatMoney(summary.partner_subsidy_total) },
  ]);
}

function renderRevenueCards(summary) {
  renderCards("#directRevenueCards", [
    { label: "实际收款总额", value: formatMoney(summary.actual_received_total) },
    { label: "合伙人收入总额", value: formatMoney(summary.partner_income_total) },
    { label: "骑手提成总计", value: formatMoney(summary.rider_commission_total) },
    { label: "经营利润", value: formatMoney(summary.partner_profit) },
    { label: "客单价", value: formatMoney(summary.avg_ticket_price) },
    { label: "骑手单均提成", value: formatMoney(summary.rider_avg_commission) },
    { label: "准时率", value: formatPercent(summary.on_time_rate) },
    { label: `SLA 履约率（${summary.sla_minutes || 30}分钟）`, value: formatPercent(summary.sla_on_time_rate) },
    { label: "SLA 超时率", value: formatPercent(summary.sla_overtime_rate) },
  ]);
}

function renderRiderCommissionTable(rows) {
  renderTable(
    "#directRiderCommissionTable",
    [
      { key: "rider_id", label: "骑手ID" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "rider_commission_total", label: "骑手提成", render: formatMoney, align: "right" },
      { key: "rider_avg_commission", label: "骑手单均提成", render: formatMoney, align: "right" },
    ],
    rows,
    { emptyText: "当前筛选范围内暂无骑手提成明细" },
  );
}

async function runPage() {
  const filters = directFilters();
  if (!filters.partner_id) {
    clearPanels();
    return;
  }

  const [cancelDaily, hourly, sources, coupons, riderIncome] = await Promise.all([
    api("/api/v1/direct/cancel-daily", filters),
    api("/api/v1/direct/hourly", filters),
    api("/api/v1/direct/order-sources", filters),
    api("/api/v1/direct/coupons", filters),
    api(`/api/v1/partner/${filters.partner_id}/income/riders`, filters),
  ]);

  const summary = cancelDaily.summary || {};
  const cancelItems = cancelDaily.items || [];
  const hourlyItems = (hourly.hourly_summary || []).map((item) => ({
    ...item,
    efficiency: safeEfficiency(item.completed_orders, item.accepted_rider_count),
  }));

  renderConclusion(summary);
  renderSummaryCards(summary);
  renderRevenueCards(summary);

  renderLineChart("#directDayChart", cancelItems.map((item) => item.date), [
    { name: "总订单", values: cancelItems.map((item) => item.total_orders) },
    { name: "完成订单", values: cancelItems.map((item) => item.completed_orders) },
    { name: "取消订单", values: cancelItems.map((item) => item.cancelled_orders) },
  ]);

  renderLineChart("#directEffectiveChart", cancelItems.map((item) => item.date), [
    { name: "有效订单", values: cancelItems.map((item) => item.valid_orders) },
    { name: "有效完成订单", values: cancelItems.map((item) => item.valid_completed_orders) },
    { name: "有效取消订单", values: cancelItems.map((item) => item.valid_cancel_orders) },
  ]);

  renderTable(
    "#directCancelTable",
    [
      { key: "date", label: "日期", render: (value, row) => value || row.label || "-" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "completion_rate", label: "完成率", render: formatPercent, align: "right" },
      { key: "cancel_rate", label: "取消率", render: formatPercent, align: "right" },
    ],
    appendTotalRow(cancelItems, ["total_orders", "completed_orders", "cancelled_orders"]),
  );

  renderTable(
    "#directEffectiveTable",
    [
      { key: "date", label: "日期", render: (value, row) => value || row.label || "-" },
      { key: "valid_orders", label: "有效订单", render: formatNumber, align: "right" },
      { key: "valid_completed_orders", label: "有效完成订单", render: formatNumber, align: "right" },
      { key: "valid_completion_rate", label: "有效订单完成率", render: formatPercent, align: "right" },
      { key: "valid_cancel_orders", label: "有效取消订单", render: formatNumber, align: "right" },
      { key: "valid_cancel_rate", label: "有效订单取消率", render: formatPercent, align: "right" },
      { key: "on_time_rate", label: "准时率", render: formatPercent, align: "right" },
      { key: "sla_on_time_rate", label: "SLA 履约率", render: formatPercent, align: "right" },
      { key: "sla_overtime_rate", label: "SLA 超时率", render: formatPercent, align: "right" },
    ],
    appendTotalRow(cancelItems, ["valid_orders", "valid_completed_orders", "valid_cancel_orders"]),
  );

  renderTable(
    "#directHourlyTable",
    [
      { key: "hour", label: "小时", render: (value, row) => value ?? row.label ?? "-" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "valid_orders", label: "有效订单", render: formatNumber, align: "right" },
      { key: "valid_completed_orders", label: "有效完成订单", render: formatNumber, align: "right" },
      { key: "accepted_rider_count", label: "接单骑手数", render: formatNumber, align: "right" },
      { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
      { key: "on_time_rate", label: "准时率", render: formatPercent, align: "right" },
      { key: "sla_on_time_rate", label: "SLA 履约率", render: formatPercent, align: "right" },
      { key: "sla_overtime_rate", label: "SLA 超时率", render: formatPercent, align: "right" },
      { key: "avg_ticket_price", label: "订单均价", render: formatMoney, align: "right" },
      { key: "rider_avg_commission", label: "骑手单均提成", render: formatMoney, align: "right" },
    ],
    appendTotalRow(
      hourlyItems,
      ["total_orders", "completed_orders", "cancelled_orders", "valid_orders", "valid_completed_orders", "accepted_rider_count", "on_time_orders", "sla_on_time_orders", "sla_overtime_orders"],
      "hour",
    ),
  );

  renderTable(
    "#directSourceTable",
    [
      { key: "order_source", label: "下单来源", render: (value, row) => value || row.label || "-" },
      { key: "current_total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "current_completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "current_cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "current_valid_orders", label: "有效订单", render: formatNumber, align: "right" },
      { key: "current_valid_completed_orders", label: "有效完成订单", render: formatNumber, align: "right" },
    ],
    appendTotalRow(
      sources.items || [],
      ["current_total_orders", "current_completed_orders", "current_cancelled_orders", "current_valid_orders", "current_valid_completed_orders"],
    ),
  );

  renderTable(
    "#directCouponTable",
    [
      { key: "coupon_label", label: "统计口径" },
      { key: "coupon_order_count", label: "券单量", render: formatNumber, align: "right" },
      { key: "hq_discount_total", label: "总部优惠金额", render: formatMoney, align: "right" },
      { key: "discount_total", label: "优惠金额", render: formatMoney, align: "right" },
      { key: "total_discount", label: "总优惠金额", render: formatMoney, align: "right" },
    ],
    coupons.items || [],
    { emptyText: "当前筛选范围内暂无优惠金额统计" },
  );

  renderRiderCommissionTable(riderIncome.items || []);
}

function bindEvents() {
  requireElement("#refreshDirect", "刷新按钮").addEventListener("click", () => runPage().catch(showError));
  [
    ["#directStartDate", "开始日期"],
    ["#directEndDate", "结束日期"],
    ["#directActiveThreshold", "活跃完成单阈值"],
    ["#directValidCancelThreshold", "有效取消阈值"],
  ].forEach(([selector, label]) => {
    requireElement(selector, label).addEventListener("change", () => runPage().catch(showError));
  });
}

async function bootstrap() {
  clearPanels();
  const meta = await api("/api/v1/meta");
  populateFilters(meta);
  bindEvents();
}

bootstrap().catch(showError);
