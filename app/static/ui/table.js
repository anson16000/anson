import { escapeHtml, requireElement } from "/static/ui/base.js";

function alignClass(value = "left") {
  return value === "right" ? "text-right" : value === "center" ? "text-center" : "";
}

function sortIcon(active, dir) {
  if (!active) return " ↕";
  return dir === "asc" ? " ▲" : " ▼";
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
    const col = columns.find((item) => item.key === key);
    const sortType = col?.sortType || "auto";
    sortedRows = [...rows].sort((a, b) => {
      const av = a?.[key];
      const bv = b?.[key];
      if (av == null || av === "-") return 1;
      if (bv == null || bv === "-") return -1;
      if (sortType === "string") {
        return dir === "asc"
          ? String(av).localeCompare(String(bv), "zh-CN")
          : String(bv).localeCompare(String(av), "zh-CN");
      }
      const an = Number(av);
      const bn = Number(bv);
      if (!Number.isNaN(an) && !Number.isNaN(bn)) {
        return dir === "asc" ? an - bn : bn - an;
      }
      return dir === "asc"
        ? String(av).localeCompare(String(bv), "zh-CN")
        : String(bv).localeCompare(String(av), "zh-CN");
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
        if (!column.sortable) {
          return `<th class="${cls}">${escapeHtml(column.label)}</th>`;
        }
        const active = currentSortKey === column.key;
        return `<th class="${cls} sortable${active ? " sort-active" : ""}" data-key="${column.key}">${escapeHtml(column.label)}<span class="sort-icon">${sortIcon(active, currentSortDir)}</span></th>`;
      })
      .join("");
    const row = host.querySelector("thead tr");
    if (row) row.innerHTML = html;
  }

  function renderBody() {
    const html = sortedRows
      .map((row) => {
        const cells = columns
          .map((column) => {
            const rawValue = row?.[column.key];
            let displayValue = rawValue;
            if (column.render) displayValue = column.render(rawValue, row);
            let content = escapeHtml(displayValue ?? "-");
            if (column.href && rawValue != null) {
              const url = typeof column.href === "function"
                ? column.href(rawValue, row)
                : column.href.replace("{value}", encodeURIComponent(rawValue));
              content = `<a class="table-link" href="${url}">${content}</a>`;
            }
            return `<td class="${alignClass(column.align)}">${content}</td>`;
          })
          .join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");
    const body = host.querySelector("tbody");
    if (body) body.innerHTML = html;
  }

  const headHtml = columns
    .map((column) => {
      const cls = alignClass(column.align);
      if (!column.sortable) {
        return `<th class="${cls}">${escapeHtml(column.label)}</th>`;
      }
      const active = currentSortKey === column.key;
      return `<th class="${cls} sortable${active ? " sort-active" : ""}" data-key="${column.key}">${escapeHtml(column.label)}<span class="sort-icon">${sortIcon(active, currentSortDir)}</span></th>`;
    })
    .join("");

  const bodyHtml = sortedRows
    .map((row) => {
      const cells = columns
        .map((column) => {
          const rawValue = row?.[column.key];
          let displayValue = rawValue;
          if (column.render) displayValue = column.render(rawValue, row);
          let content = escapeHtml(displayValue ?? "-");
          if (column.href && rawValue != null) {
            const url = typeof column.href === "function"
              ? column.href(rawValue, row)
              : column.href.replace("{value}", encodeURIComponent(rawValue));
            content = `<a class="table-link" href="${url}">${content}</a>`;
          }
          return `<td class="${alignClass(column.align)}">${content}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  host.innerHTML = `
    <table class="data-table">
      <thead><tr>${headHtml}</tr></thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;

  if (currentSortKey) {
    doSort(currentSortKey, currentSortDir);
  }

  host.querySelector("thead")?.addEventListener("click", (event) => {
    const th = event.target.closest("th.sortable");
    if (!th || event.target.closest("a")) return;
    const key = th.dataset.key;
    const dir = currentSortKey === key && currentSortDir === "desc" ? "asc" : "desc";
    doSort(key, dir);
  });

  host.querySelector("tbody")?.addEventListener("click", (event) => {
    const link = event.target.closest("a.table-link");
    if (!link) return;
    event.stopPropagation();
    try {
      const url = new URL(link.href, window.location.origin);
      const partnerId = url.searchParams.get("partner_id");
      if (partnerId) {
        const data = JSON.parse(sessionStorage.getItem("dashboard_filters") || "{}");
        data._shared_partner_id = partnerId;
        sessionStorage.setItem("dashboard_filters", JSON.stringify(data));
      }
    } catch (_) {
      // ignore malformed links
    }
  });
}

export function renderCards(selector, cards) {
  const host = requireElement(selector);
  host.innerHTML = (cards || [])
    .map((item) => `
      <article class="card metric-card">
        <span class="metric-label">${escapeHtml(item.label)}</span>
        <strong class="metric-value">${escapeHtml(item.value ?? "-")}</strong>
      </article>
    `)
    .join("");
}

export function renderTags(selector, tags, options = {}) {
  const host = requireElement(selector);
  const emptyText = options.emptyText || "暂无诊断摘要";
  if (!tags || !tags.length) {
    host.innerHTML = `<div class="empty empty-inline">${escapeHtml(emptyText)}</div>`;
    return;
  }
  host.innerHTML = tags.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}
