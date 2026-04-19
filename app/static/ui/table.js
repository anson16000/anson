import { $, escapeHtml } from "/static/ui/base.js";

export function renderCards(containerId, items) {
  const container = $(containerId);
  if (!container) return;
  container.innerHTML = items
    .map(
      (item) => `
        <div class="kpi">
          <span>${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
        </div>
      `,
    )
    .join("");
}

function resolveCellClass(column, value, row) {
  const classes = [];
  if (column.align) classes.push(`align-${column.align}`);
  if (column.cellClass) {
    const computed = typeof column.cellClass === "function" ? column.cellClass(value, row) : column.cellClass;
    if (computed) classes.push(computed);
  }
  return classes.join(" ");
}

function resolveHeaderClass(column) {
  const classes = [];
  if (column.align) classes.push(`align-${column.align}`);
  if (column.headerClass) classes.push(column.headerClass);
  return classes.join(" ");
}

export function renderTable(containerId, columns, rows, options = {}) {
  const container = $(containerId);
  if (!container) return;
  if (!rows || !rows.length) {
    container.innerHTML = `<div class="empty empty-inline">${escapeHtml(options.emptyText || "当前筛选范围暂无数据")}</div>`;
    return;
  }

  const head = columns
    .map((column) => `<th class="${escapeHtml(resolveHeaderClass(column))}">${escapeHtml(column.label)}</th>`)
    .join("");

  const body = rows
    .map((row) => {
      const rowClass = options.rowClass ? options.rowClass(row) : "";
      const cells = columns
        .map((column) => {
          const raw = column.render ? column.render(row[column.key], row) : (row[column.key] ?? "-");
          const className = resolveCellClass(column, row[column.key], row);
          return `<td class="${escapeHtml(className)}">${escapeHtml(raw)}</td>`;
        })
        .join("");
      return `<tr class="${escapeHtml(rowClass || "")}">${cells}</tr>`;
    })
    .join("");

  container.innerHTML = `<table class="report-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

export function renderTags(containerId, items) {
  const container = $(containerId);
  if (!container) return;
  if (!items || !items.length) {
    container.innerHTML = '<div class="empty empty-inline">暂无诊断摘要</div>';
    return;
  }
  container.innerHTML = items.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}
