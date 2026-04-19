import {
  formatDecimal,
  formatMoney,
  formatNumber,
  formatPercent,
  renderCards,
  renderLineChart,
  renderTable,
  renderTags,
  setHtml,
} from "/static/common.js";
import { requireElement } from "/static/ui/base.js";

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
  const sp = getSharedPartnerParam();
  setHtml("#adminDrillLinks", `
    <a class="drill-link" href="/alerts${sp}">查看风险区域和预警详情</a>
    <a class="drill-link" href="/partner/hourly${sp}">查看时段热力与履约</a>
    <a class="drill-link" href="/partner/entities${sp}">查看主体结构分析</a>
  `);
}

export function renderAdminSummaryCards(metrics) {
  const summary = metrics.summary || {};
  renderCards("#adminCards .kpi-tier-result", [
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "完成订单/有效订单", value: formatPercent(summary.completed_orders / summary.valid_orders || 0) },
    { label: "取消率", value: formatPercent(summary.cancel_rate) },
    { label: "经营利润", value: formatMoney(summary.partner_profit_total) },
    { label: "风险区域数", value: formatNumber(metrics.risk_partner_items?.length || 0) },
  ]);
  renderCards("#adminCards .kpi-tier-process", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
  ]);
  renderCards("#adminCards .kpi-tier-action", [
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
    { label: "新合伙人", value: formatNumber(summary.new_partners) },
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
  const sp = getSharedPartnerParam();
  renderTable(
    "#regionRankingTable",
    [
      { key: "partner_id", label: "合伙人ID", sortable: true, sortType: "string" },
      {
        key: "region",
        label: "区域",
        sortable: true,
        href: (value, row) => {
          if (row.partner_id) return `/partner?partner_id=${encodeURIComponent(row.partner_id)}${sp}`;
          return "#";
        },
      },
      { key: "total_orders", label: "总订单", sortable: true, render: formatNumber, align: "right" },
      { key: "valid_orders", label: "有效订单", sortable: true, render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", sortable: true, render: formatNumber, align: "right" },
      { key: "completion_rate", label: "完成率", sortable: true, render: formatPercent, align: "right" },
      { key: "cancel_rate", label: "取消率", sortable: true, render: formatPercent, align: "right" },
      { key: "efficiency", label: "人效", sortable: true, render: formatDecimal, align: "right" },
      { key: "active_riders", label: "骑手人数", sortable: true, render: formatNumber, align: "right" },
      { key: "active_merchants", label: "商家数量", sortable: true, render: formatNumber, align: "right" },
      { key: "avg_ticket_price", label: "订单均价", sortable: true, render: formatMoney, align: "right" },
      { key: "partner_profit", label: "经营利润", sortable: true, render: formatMoney, align: "right" },
    ],
    rows || [],
  );
}

export function renderPartnerDailyComparison(data) {
  if (!data || !data.length) {
    requireElement("#partnerDailyComparisonTable").innerHTML = '<div class="empty empty-inline">当前暂无近3天单量对比数据</div>';
    return;
  }
  // Get unique dates and partners
  const dates = [...new Set(data.map((d) => d.date))].sort().slice(-3);
  const partnerMap = {};
  data.forEach((d) => {
    if (!partnerMap[d.partner_id]) {
      partnerMap[d.partner_id] = { partner_id: d.partner_id, partner_name: d.partner_name };
    }
    partnerMap[d.partner_id][d.date] = d.completed_orders;
  });
  const partners = Object.values(partnerMap);

  const columns = [
    { key: "partner_id", label: "合伙人ID", sortType: "string" },
    { key: "partner_name", label: "合伙人名称" },
    ...dates.map((d) => ({
      key: d,
      label: d.slice(5),
      sortable: true,
      render: (v) => (v != null ? formatNumber(v) : "-"),
      align: "right",
    })),
    {
      key: "_trend",
      label: "趋势",
      render: (v, row) => {
        const vals = dates.map((d) => row[d]).filter((x) => x != null);
        if (vals.length < 2) return "-";
        const first = vals[0];
        const last = vals[vals.length - 1];
        const diff = last - first;
        const sign = diff > 0 ? "+" : "";
        return `<span class="${diff > 0 ? "trend-up" : diff < 0 ? "trend-down" : ""}">${sign}${diff}</span>`;
      },
    },
  ];
  renderTable("#partnerDailyComparisonTable", columns, partners, { emptyText: "暂无数据" });
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

export function renderNewPartnerTable(items, selector = "#newPartnerTable", emptyText = "当前筛选范围暂无新合伙人表现数据") {
  renderTable(
    selector,
    [
      { key: "partner_id", label: "合伙人ID", sortType: "string" },
      { key: "partner_name", label: "合伙人" },
      { key: "open_date", label: "开城时间" },
      { key: "completed_orders", label: "完成订单", render: formatNumber, align: "right" },
    ],
    items || [],
    { emptyText },
  );
}

export function renderAnomalySummary(metrics) {
  const rows = metrics.region_ranking || [];
  if (!rows.length) {
    setHtml("#anomalySummary", '<div class="empty empty-inline">当前筛选范围暂无异常摘要数据</div>');
    return;
  }
  const top5LowCompletion = [...rows].sort((a, b) => (a.completion_rate || 0) - (b.completion_rate || 0)).slice(0, 5);
  const top5HighCancel = [...rows].sort((a, b) => (b.cancel_rate || 0) - (a.cancel_rate || 0)).slice(0, 5);
  const top5LowProfit = [...rows].sort((a, b) => (a.partner_profit || 0) - (b.partner_profit || 0)).slice(0, 5);
  setHtml("#anomalySummary", `
    <div class="anomaly-column">
      <h4 class="anomaly-danger">完成率最低 5 个区域</h4>
      ${top5LowCompletion.map((item, i) => `
        <div class="anomaly-item">
          <span class="anomaly-rank">${i + 1}</span>
          <span class="anomaly-name">${item.region || "-"}</span>
          <span class="anomaly-value danger">${formatPercent(item.completion_rate)}</span>
        </div>
      `).join("")}
    </div>
    <div class="anomaly-column">
      <h4 class="anomaly-warn">取消率最高 5 个区域</h4>
      ${top5HighCancel.map((item, i) => `
        <div class="anomaly-item">
          <span class="anomaly-rank">${i + 1}</span>
          <span class="anomaly-name">${item.region || "-"}</span>
          <span class="anomaly-value warn">${formatPercent(item.cancel_rate)}</span>
        </div>
      `).join("")}
    </div>
    <div class="anomaly-column">
      <h4 class="anomaly-muted">经营利润最低 5 个区域</h4>
      ${top5LowProfit.map((item, i) => `
        <div class="anomaly-item">
          <span class="anomaly-rank">${i + 1}</span>
          <span class="anomaly-name">${item.region || "-"}</span>
          <span class="anomaly-value">${formatMoney(item.partner_profit)}</span>
        </div>
      `).join("")}
    </div>
  `);
}
