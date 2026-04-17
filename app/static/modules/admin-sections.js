import {
  formatDecimal,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderLineChart,
  renderTable,
  renderTags,
} from "/static/common.js";

export function renderAdminConclusion(metrics) {
  const summary = metrics.summary || {};
  const tags = [
    `当前查询范围总订单 ${formatNumber(summary.total_orders)} 单`,
    `完成率 ${formatPercent(summary.completion_rate)}`,
    `取消率 ${formatPercent(summary.cancel_rate)}`,
  ];
  if ((summary.valid_completion_rate || 0) < 0.8) tags.push("有效订单完成率仍有提升空间");
  if ((summary.new_partners || 0) > 0) tags.push(`新合伙人 ${formatNumber(summary.new_partners)} 个，可继续跟进首月表现`);
  renderTags("#adminConclusion", tags);
}

export function renderAdminSummaryCards(metrics) {
  const summary = metrics.summary || {};
  renderCards("#adminCards", [
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

export function renderAdminTrend(metrics) {
  renderLineChart("#adminTrendChart", (metrics.daily_trend || []).map((item) => item.date), [
    { name: "总订单", values: (metrics.daily_trend || []).map((item) => item.total_orders) },
    { name: "有效订单", values: (metrics.daily_trend || []).map((item) => item.valid_orders) },
    { name: "完成订单", values: (metrics.daily_trend || []).map((item) => item.completed_orders) },
  ]);
}

export function renderRegionRanking(rows) {
  renderTable(
    "#regionRankingTable",
    [
      { key: "region", label: "区域" },
      { key: "total_orders", label: "总订单", render: formatNumber, align: "right" },
      { key: "valid_orders", label: "有效订单", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", render: formatNumber, align: "right" },
      { key: "completion_rate", label: "完成率", render: formatPercent, align: "right" },
      { key: "cancel_rate", label: "取消率", render: formatPercent, align: "right" },
      { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
      { key: "active_riders", label: "骑手人数", render: formatNumber, align: "right" },
      { key: "active_merchants", label: "商家数量", render: formatNumber, align: "right" },
      { key: "avg_ticket_price", label: "订单均价", render: formatMoney, align: "right" },
      { key: "partner_profit", label: "经营利润", render: formatMoney, align: "right" },
    ],
    rows || [],
  );
}

export function renderPartnerTierTable(items) {
  renderTable(
    "#partnerTierTable",
    [
      { key: "label", label: "日均单量层级" },
      { key: "partner_count", label: "加盟商数量", render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
      { key: "avg_daily_orders", label: "日均单量", render: formatDecimal, align: "right" },
      { key: "avg_ticket_price", label: "均单价", render: formatMoney, align: "right" },
      { key: "efficiency", label: "人效", render: formatDecimal, align: "right" },
      { key: "avg_income_per_order", label: "单均收入", render: formatMoney, align: "right" },
    ],
    items || [],
  );
}

export function renderNewPartnerTable(items) {
  renderTable(
    "#newPartnerTable",
    [
      { key: "window_label", label: "表现窗口" },
      { key: "partner_name", label: "合伙人" },
      { key: "open_date", label: "开城时间" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
    ],
    items || [],
    { emptyText: "当前筛选范围暂无新合伙人表现数据" },
  );
}
