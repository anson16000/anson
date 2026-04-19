import { escapeHtml, requireElement } from "/static/ui/base.js";

function alignClass(value = "left") {
  return value === "right" ? "text-right" : value === "center" ? "text-center" : "";
}

export function renderTable(selector, columns, rows, options = {}) {
  const host = requireElement(selector);
  const emptyText = options.emptyText || "当前筛选范围暂无数据";

  if (!rows || !rows.length) {
    host.innerHTML = `<div class="empty empty-inline">${escapeHtml(emptyText)}</div>`;
    return;
  }

  let sortedRows = [...rows];
  let currentSortKey = host.dataset.sortKey || null;
  let currentSortDir = host.dataset.sortDir || "desc";

  function doSort(key, dir) {
    const col = columns.find((c) => c.key === key);
    const sortType = col?.sortType || "auto";
    sortedRows = [...rows].sort((a, b) => {
      const av = a?.[key];
      const bv = b?.[key];
      if (av == null || av === "-") return 1;
      if (bv == null || bv === "-") return -1;
      if (sortType === "string") {
        return dir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
      }
      const an = Number(av);
      const bn = Number(bv);
      if (!isNaN(an) && !isNaN(bn) && sortType !== "string") {
        return dir === "asc" ? an - bn : bn - an;
      }
      return dir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    currentSortKey = key;
    currentSortDir = dir;
    host.dataset.sortKey = key;
    host.dataset.sortDir = dir;
    renderHead();
    renderBody();
  }

  function renderHead() {
    const html = columns
      .map((column) => {
        const cls = alignClass(column.align);
        if (column.sortable) {
          const isActive = currentSortKey === column.key;
          const icon = isActive
            ? (currentSortDir === "asc" ? " ▲" : " ▼")
            : " ⇅";
          const activeCls = isActive ? " sort-active" : "";
          return `<th class="${cls} sortable${activeCls}" data-key="${column.key}">${escapeHtml(column.label)}<span class="sort-icon">${icon}</span></th>`;
        }
        return `<th class="${cls}">${escapeHtml(column.label)}</th>`;
      })
      .join("");
    const theadRow = host.querySelector("thead tr");
    if (theadRow) theadRow.innerHTML = html;
  }

  function renderBody() {
    const html = sortedRows
      .map((row) => {
        const cells = columns.map((column) => {
          const rawValue = row?.[column.key];
          let displayValue = rawValue;
          if (column.render) {
            displayValue = column.render(rawValue, row);
          }
          let cellContent = escapeHtml(displayValue ?? "-");
          if (column.href && rawValue != null) {
            const url = typeof column.href === "function" ? column.href(rawValue, row) : column.href.replace("{value}", encodeURIComponent(rawValue));
            cellContent = `<a class="table-link" href="${url}">${cellContent}</a>`;
          }
          return `<td class="${alignClass(column.align)}">${cellContent}</td>`;
        });
        return `<tr>${cells.join("")}</tr>`;
      })
      .join("");
    const tbodyEl = host.querySelector("tbody");
    if (tbodyEl) tbodyEl.innerHTML = html;
  }

  function buildTable() {
    const theadHtml = columns
      .map((column) => {
        const cls = alignClass(column.align);
        if (column.sortable) {
          const isActive = currentSortKey === column.key;
          const icon = isActive
            ? (currentSortDir === "asc" ? " ▲" : " ▼")
            : " ⇅";
          const activeCls = isActive ? " sort-active" : "";
          return `<th class="${cls} sortable${activeCls}" data-key="${column.key}">${escapeHtml(column.label)}<span class="sort-icon">${icon}</span></th>`;
        }
        return `<th class="${cls}">${escapeHtml(column.label)}</th>`;
      })
      .join("");

    const tbodyHtml = sortedRows
      .map((row) => {
        const cells = columns.map((column) => {
          const rawValue = row?.[column.key];
          let displayValue = rawValue;
          if (column.render) {
            displayValue = column.render(rawValue, row);
          }
          let cellContent = escapeHtml(displayValue ?? "-");
          if (column.href && rawValue != null) {
            const url = typeof column.href === "function" ? column.href(rawValue, row) : column.href.replace("{value}", encodeURIComponent(rawValue));
            cellContent = `<a class="table-link" href="${url}">${cellContent}</a>`;
          }
          return `<td class="${alignClass(column.align)}">${cellContent}</td>`;
        });
        return `<tr>${cells.join("")}</tr>`;
      })
      .join("");

    host.innerHTML = `
      <table class="data-table">
        <thead><tr>${theadHtml}</tr></thead>
        <tbody>${tbodyHtml}</tbody>
      </table>
    `;
  }

  buildTable();

  // Apply initial sort if specified
  if (currentSortKey) {
    doSort(currentSortKey, currentSortDir);
  }

  // Bind sort events on thead
  host.querySelector("thead").addEventListener("click", (e) => {
    const th = e.target.closest("th.sortable");
    if (!th) return;
    // Don't sort if clicking a link inside the header
    if (e.target.closest("a")) return;
    const key = th.dataset.key;
    const dir = currentSortKey === key && currentSortDir === "desc" ? "asc" : "desc";
    doSort(key, dir);
  });

  // Allow links in table body to work normally (no sort interference)
  host.querySelector("tbody").addEventListener("click", (e) => {
    const link = e.target.closest("a.table-link");
    if (!link) return;
    e.stopPropagation();
    // Save shared partner_id to sessionStorage before navigation
    try {
      const url = new URL(link.href, window.location.origin);
      const partnerId = url.searchParams.get("partner_id");
      if (partnerId) {
        const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
        data._shared_partner_id = partnerId;
        sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
      }
    } catch (_) { /* ignore */ }
  });
}

export function renderCards(selector, cards) {
  const host = requireElement(selector);
  host.innerHTML = (cards || [])
    .map(
      (item) => `
        <article class="card metric-card">
          <span class="metric-label">${escapeHtml(item.label)}</span>
          <strong class="metric-value">${escapeHtml(item.value ?? "-")}</strong>
        </article>
      `,
    )
    .join("");
}

export function renderTags(selector, tags, options = {}) {
  const host = requireElement(selector);
  const emptyText = options.emptyText || "暂无诊断摘要";
  if (!tags || !tags.length) {
    host.innerHTML = `<div class="empty empty-inline">${escapeHtml(emptyText)}</div>`;
    return;
  }
  host.innerHTML = tags
    .map((item) => `<span class="tag">${escapeHtml(item)}</span>`)
    .join("");
}
