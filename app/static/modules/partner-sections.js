import {
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderLineChart,
  renderTable,
  renderTags,
  setHtml,
} from "/static/common.js";

function getSharedPartnerParam() {
  try {
    const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
    const pid = data._shared_partner_id;
    const sd = data._shared_start_date;
    const ed = data._shared_end_date;
    const params = new URLSearchParams();
    if (pid) params.set("partner_id", pid);
    if (sd) params.set("start_date", sd);
    if (ed) params.set("end_date", ed);
    const str = params.toString();
    return str ? `?${str}` : "";
  } catch (_) {
    return "";
  }
}

export function renderPartnerSummary(overview) {
  const summary = overview.summary || {};
  const diagnostics = overview.diagnostics || [];
  renderTags("#partnerConclusion", diagnostics);
  renderCards("#partnerCards .kpi-tier-result", [
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "完成订单/有效订单", value: formatPercent(summary.completed_orders / summary.valid_orders || 0) },
    { label: "经营利润", value: formatMoney(summary.partner_profit) },
    { label: "SLA 履约率", value: formatPercent(summary.sla_on_time_rate) },
  ]);
  renderCards("#partnerCards .kpi-tier-process", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
  ]);
  renderCards("#partnerCards .kpi-tier-action", [
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
    { label: "总部补贴", value: formatMoney(summary.hq_subsidy_total) },
    { label: "合伙人补贴", value: formatMoney(summary.partner_subsidy_total) },
    { label: "实际收款总", value: formatMoney(summary.actual_received_total) },
    { label: "订单均价", value: formatMoney(summary.avg_ticket_price) },
  ]);
}

export function renderPartnerDailyTrend(daily) {
  const items = daily.items || [];
  renderLineChart("#partnerDailyChart", items.map((item) => item.date), [
    { name: "总订单", values: items.map((item) => item.total_orders) },
    { name: "有效订单", values: items.map((item) => item.valid_orders) },
    { name: "完成订单", values: items.map((item) => item.completed_orders) },
    { name: "取消订单", values: items.map((item) => item.cancelled_orders) },
  ]);
}

export function renderPartnerFinance(daily) {
  const items = daily.items || [];
  renderLineChart("#partnerFinanceChart", items.map((item) => item.date), [
    { name: "实际收款", values: items.map((item) => item.actual_received_total) },
    { name: "骑手提成", values: items.map((item) => item.rider_commission_total) },
    { name: "经营利润", values: items.map((item) => item.partner_profit) },
  ]);
  renderTable(
    "#partnerFinanceTable",
    [
      { key: "date", label: "日期" },
      { key: "actual_received_total", label: "实际收款总额", render: formatMoney, align: "right" },
      { key: "rider_commission_total", label: "骑手提成总计", render: formatMoney, align: "right" },
      { key: "partner_income_total", label: "合伙人收入总额", render: formatMoney, align: "right" },
      { key: "partner_subsidy_total", label: "合伙人补贴总额", render: formatMoney, align: "right" },
      { key: "partner_profit", label: "经营利润", render: formatMoney, align: "right" },
      { key: "on_time_rate", label: "准时率", render: formatPercent, align: "right" },
      { key: "sla_on_time_rate", label: "SLA 履约率", render: formatPercent, align: "right" },
    ],
    items,
    { emptyText: "当前筛选范围暂无经营收益明细" },
  );
}

export function renderDirectSpecialSummary(directData) {
  const summary = directData.summary || {};
  const tags = [
    `有效订单取消率 ${formatPercent(summary.valid_cancel_rate)}`,
    `SLA 履约率 ${formatPercent(summary.sla_on_time_rate)}`,
  ];
  if ((summary.cancel_rate || 0) >= 0.2) tags.push("取消率偏高，建议进入时段页排查高峰问题");
  renderTags("#directSpecialTags", tags);
  renderCards("#directSpecialCards", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "经营利润", value: formatMoney(summary.partner_profit) },
    { label: "骑手提成总计", value: formatMoney(summary.rider_commission_total) },
  ]);
}

export function renderIssueSummary(overview, directData) {
  const summary = overview.summary || {};
  const directSummary = directData.summary || {};
  const tags = [];
  if ((summary.cancel_rate || 0) >= 0.2) tags.push("城市取消率偏高，建议进入时段热力与履约页查看高峰承接和热力图");
  if ((summary.on_time_rate || 0) < 0.8) tags.push("准时率偏低，建议关注小时运力和 SLA 履约率");
  if ((directSummary.valid_cancel_rate || 0) >= 0.08) tags.push("有效取消偏高，建议查看时段数据与渠道对比");
  if ((summary.new_riders || 0) > 0 || (summary.new_merchants || 0) > 0) tags.push("如需查看新主体明细，请进入主体分析页");
  if (!tags.length) tags.push("当前经营整体平稳，可进入专题页查看细分模块。");
  renderTags("#issueSummaryTags", tags);
  setHtml("#partnerDrillLinks", `
    <a class="drill-link" href="/partner/hourly${getSharedPartnerParam()}">时段履约：查看高峰 SLA 和供需热力</a>
    <a class="drill-link" href="/partner/entities${getSharedPartnerParam()}">主体分析：查看新增主体和贡献结构</a>
    <a class="drill-link" href="/alerts${getSharedPartnerParam()}">诊断预警：查看风险名单和波动预警</a>
  `);
}
