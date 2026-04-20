import {
  escapeHtml,
  formatMoney,
  formatNumber,
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
    return pid ? `?partner_id=${encodeURIComponent(pid)}` : "";
  } catch (_) {
    return "";
  }
}

function yesNo(value) {
  return Number(value || 0) === 1 ? "是" : "否";
}

export function renderEntitiesSummary(overview) {
  const summary = overview.summary || {};
  renderTags("#entitiesConclusion", [
    `新骑手数 ${formatNumber(summary.new_riders)}`,
    `新商家数 ${formatNumber(summary.new_merchants)}`,
    `活跃骑手数 ${formatNumber(summary.active_riders)}`,
    `活跃商家数 ${formatNumber(summary.active_merchants)}`,
  ]);
  setHtml(
    "#entitiesDrillLinks",
    `
      <a class="drill-link" href="/alerts">诊断预警：查看风险名单和健康度</a>
      <a class="drill-link" href="/partner${getSharedPartnerParam()}">城市经营：查看经营收益明细</a>
    `,
  );
  renderCards("#entitiesCards .kpi-tier-result", [
    { label: "完成订单", value: formatNumber(summary.completed_orders) },
    { label: "活跃骑手数", value: formatNumber(summary.active_riders) },
    { label: "活跃商家数", value: formatNumber(summary.active_merchants) },
  ]);
  renderCards("#entitiesCards .kpi-tier-process", [
    { label: "总订单", value: formatNumber(summary.total_orders) },
    { label: "有效订单", value: formatNumber(summary.valid_orders) },
    { label: "取消订单", value: formatNumber(summary.cancelled_orders) },
    { label: "骑手提成总计", value: formatMoney(summary.rider_commission_total) },
  ]);
  renderCards("#entitiesCards .kpi-tier-action", [
    { label: "新骑手数", value: formatNumber(summary.new_riders) },
    { label: "新商家数", value: formatNumber(summary.new_merchants) },
  ]);
}

export function renderEntityContributionCharts(newRiders, newMerchants) {
  const riderSeries = newRiders.daily || [];
  const merchantSeries = newMerchants.daily || [];
  renderLineChart("#entitiesRiderChart", riderSeries.map((item) => item.date), [
    { name: "新骑手完成订单", values: riderSeries.map((item) => item.completed_orders) },
  ]);
  renderLineChart("#entitiesMerchantChart", merchantSeries.map((item) => item.date), [
    { name: "新商家完成订单", values: merchantSeries.map((item) => item.completed_orders) },
  ]);
}

export function renderMerchantIdentity(rows) {
  renderTable(
    "#merchantLikeUsersTable",
    [
      { key: "user_id", label: "用户 ID", sortType: "string" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
    ],
    rows || [],
    { emptyText: "当前阈值下暂无商家型用户" },
  );
}

export function renderCommission(rows) {
  renderTable(
    "#entitiesCommissionTable",
    [
      { key: "rider_id", label: "骑手 ID", sortType: "string" },
      { key: "rider_name", label: "骑手姓名" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
      { key: "rider_commission_total", label: "骑手提成", sortable: true, render: formatMoney, align: "right" },
      { key: "rider_avg_commission", label: "骑手单均提成", sortable: true, render: formatMoney, align: "right" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无骑手提成明细" },
  );
}

export function renderRiderRoster(rows) {
  renderTable(
    "#entitiesRiderRosterTable",
    [
      { key: "rider_id", label: "骑手 ID", sortable: true, sortType: "string" },
      { key: "rider_name", label: "骑手姓名", sortable: true },
      { key: "hire_date", label: "入职时间", sortable: true },
      { key: "total_orders", label: "总订单", sortable: true, render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", sortable: true, render: formatNumber, align: "right" },
      { key: "is_new_rider", label: "是否新骑手", render: yesNo, align: "center" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无骑手名单" },
  );
}

export function renderMerchantRoster(rows) {
  renderTable(
    "#entitiesMerchantRosterTable",
    [
      { key: "merchant_id", label: "商家 ID", sortable: true, sortType: "string" },
      { key: "merchant_name", label: "商户名称", sortable: true },
      { key: "register_date", label: "注册时间", sortable: true },
      { key: "total_orders", label: "总订单", sortable: true, render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", sortable: true, render: formatNumber, align: "right" },
      { key: "is_new_merchant", label: "是否新商家", render: yesNo, align: "center" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无商家名单" },
  );
}

export function renderOrderSourceSummary(payload) {
  const hostSelector = "#entitiesOrderSourceSummary";
  const items = payload?.items || [];
  if (!items.length) {
    setHtml(hostSelector, '<div class="empty empty-inline">当前筛选范围暂无订单来源数据</div>');
    return;
  }

  const maxOrders = Math.max(...items.map((item) => Number(item.total_orders || 0)), 1);
  const totalOrders = Number(payload?.summary?.total_orders || 0) || items.reduce((sum, item) => sum + Number(item.total_orders || 0), 0);

  setHtml(
    hostSelector,
    `
      <div class="order-source-summary">
        ${items
          .map((item) => {
            const orders = Number(item.total_orders || 0);
            const ratio = totalOrders > 0 ? ((orders / totalOrders) * 100).toFixed(1) : "0.0";
            const width = Math.max((orders / maxOrders) * 100, orders > 0 ? 6 : 0);
            return `
              <article class="order-source-card">
                <div class="order-source-card-head">
                  <strong>${escapeHtml(item.order_source || "未知")}</strong>
                  <span>${formatNumber(orders)} 单</span>
                </div>
                <div class="order-source-bar">
                  <span style="width:${width}%"></span>
                </div>
                <div class="order-source-meta">
                  <span>占比 ${ratio}%</span>
                  <span>有效完成 ${formatNumber(item.valid_completed_orders)}</span>
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `,
  );
}

export function renderOrderSourceTable(rows) {
  renderTable(
    "#entitiesOrderSourceTable",
    [
      { key: "order_source", label: "订单来源", sortable: true, sortType: "string" },
      { key: "total_orders", label: "总订单", sortable: true, render: formatNumber, align: "right" },
      { key: "valid_orders", label: "有效订单", sortable: true, render: formatNumber, align: "right" },
      { key: "completed_orders", label: "完成订单", sortable: true, render: formatNumber, align: "right" },
      { key: "cancelled_orders", label: "取消订单", sortable: true, render: formatNumber, align: "right" },
      { key: "valid_completed_orders", label: "有效完成订单", sortable: true, render: formatNumber, align: "right" },
    ],
    rows || [],
    { emptyText: "当前筛选范围暂无订单来源数据" },
  );
}
