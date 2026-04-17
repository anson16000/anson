export const $ = (selector) => document.querySelector(selector);

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function requireElement(selector, description = selector) {
  const element = $(selector);
  if (!element) {
    throw new Error(`页面缺少必要节点：${description}（${selector}）`);
  }
  return element;
}

export async function api(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined || value === false) return;
    url.searchParams.set(key, value);
  });
  const response = await fetch(url);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
      else if (payload?.message) detail = payload.message;
    } catch {
      // ignore non-json error body
    }
    throw new Error(detail);
  }
  const payload = await response.json();
  if (payload.code !== 200) throw new Error(payload.message || "接口返回异常");
  return payload.data;
}

export function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

export function formatPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

export function formatMoney(value) {
  return `¥${new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))}`;
}

export function formatDecimal(value) {
  return Number(value || 0).toFixed(2);
}

export function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value || "-";
}

export function setHtml(selector, html) {
  const element = $(selector);
  if (element) element.innerHTML = html;
}

export function renderSystemMeta(meta, options = {}) {
  const prefix = options.prefix || "";
  setText(`#${prefix}lastImportTime`, meta.system.last_import_time || "-");
  setText(`#${prefix}latestDataDate`, meta.system.latest_data_date || "-");
  setText(`#${prefix}dataVersion`, meta.system.data_version || "-");
}

export function toDateInputValue(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  if (!Number.isFinite(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

export function setDateRange(startSelector, endSelector, latestDateText) {
  const startInput = $(startSelector);
  const endInput = $(endSelector);
  if (!startInput || !endInput) return;
  if (startInput.value && endInput.value) return;

  const latestDate = latestDateText ? new Date(`${latestDateText}T00:00:00`) : new Date();
  if (!Number.isFinite(latestDate.getTime())) return;

  const startDate = new Date(latestDate);
  startDate.setDate(startDate.getDate() - 30);

  if (!endInput.value) endInput.value = latestDate.toISOString().slice(0, 10);
  if (!startInput.value) startInput.value = startDate.toISOString().slice(0, 10);
}

function readDateValue(value) {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isFinite(date.getTime()) ? date : null;
}

export function validateDateRange(startDateText, endDateText, maxDays = 31) {
  const startDate = readDateValue(startDateText);
  const endDate = readDateValue(endDateText);
  if (!startDate || !endDate) {
    throw new Error("请选择开始日期和结束日期。");
  }
  if (startDate > endDate) {
    throw new Error("开始日期不能晚于结束日期。");
  }
  const dayCount = Math.floor((endDate - startDate) / 86400000) + 1;
  if (dayCount > maxDays) {
    throw new Error(`单次查询最多支持 ${maxDays} 天，请缩小日期范围。`);
  }
  return {
    startDate,
    endDate,
    dayCount,
    startDateText,
    endDateText,
  };
}

export function validateDateRangeBySelectors(startSelector, endSelector, maxDays = 31) {
  return validateDateRange(
    requireElement(startSelector, "开始日期").value,
    requireElement(endSelector, "结束日期").value,
    maxDays,
  );
}

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

export function renderLineChart(containerId, labels, series) {
  const container = $(containerId);
  if (!container) return;
  if (!labels.length || !series.length) {
    container.innerHTML = '<div class="empty empty-inline">暂无趋势数据</div>';
    return;
  }

  const width = 760;
  const height = container.classList.contains("tall") ? 320 : 240;
  const margin = { top: 28, right: 16, bottom: 34, left: 52 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const allValues = series.flatMap((item) => item.values.map((value) => Number(value || 0)));
  const maxValue = Math.max(...allValues, 1);
  const stepX = labels.length > 1 ? chartWidth / (labels.length - 1) : chartWidth;
  const colors = ["#217346", "#5b708b", "#c88425", "#c75146"];

  const linePath = (values) =>
    values
      .map((value, index) => {
        const x = margin.left + stepX * index;
        const y = margin.top + chartHeight - (Number(value || 0) / maxValue) * chartHeight;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");

  const gridLines = [0, 0.25, 0.5, 0.75, 1]
    .map((ratio) => {
      const y = margin.top + chartHeight - chartHeight * ratio;
      const value = Math.round(maxValue * ratio);
      return `
        <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="#d9dfe7" stroke-width="1" />
        <text x="8" y="${y + 4}" class="axis-label">${formatNumber(value)}</text>
      `;
    })
    .join("");

  const xLabels = labels
    .map((label, index) => {
      const x = margin.left + stepX * index;
      const text = String(label).length > 5 ? String(label).slice(5) : String(label);
      return `<text x="${x}" y="${height - 10}" text-anchor="middle" class="axis-label">${escapeHtml(text)}</text>`;
    })
    .join("");

  const legend = series
    .map(
      (item, index) => `
        <g transform="translate(${margin.left + index * 168}, 12)">
          <rect x="-2" y="-5" width="10" height="10" rx="2" fill="${colors[index % colors.length]}" />
          <text x="14" y="4" class="axis-label">${escapeHtml(item.name)}</text>
        </g>
      `,
    )
    .join("");

  const paths = series
    .map((item, index) => {
      const color = colors[index % colors.length];
      const dots = item.values
        .map((value, pointIndex) => {
          const x = margin.left + stepX * pointIndex;
          const y = margin.top + chartHeight - (Number(value || 0) / maxValue) * chartHeight;
          return `<circle cx="${x}" cy="${y}" r="2.8" fill="${color}" />`;
        })
        .join("");
      return `<path d="${linePath(item.values)}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />${dots}`;
    })
    .join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      ${gridLines}
      <line x1="${margin.left}" y1="${margin.top + chartHeight}" x2="${width - margin.right}" y2="${margin.top + chartHeight}" stroke="#cfd8e3" stroke-width="1" />
      ${xLabels}
      ${legend}
      ${paths}
    </svg>
  `;
}

function heatColor(value, max, mode) {
  if (!max || value <= 0) return "#f5f7f9";
  const ratio = Math.max(0.15, value / max);
  if (mode === "cancel") return `rgba(196, 132, 37, ${Math.min(ratio, 0.95)})`;
  if (mode === "rate") return `rgba(91, 112, 139, ${Math.min(ratio, 0.95)})`;
  return `rgba(33, 115, 70, ${Math.min(ratio, 0.95)})`;
}

export function renderHeatmap(containerId, items, valueKey, mode = "count") {
  const container = $(containerId);
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="empty empty-inline">暂无热力图数据</div>';
    return;
  }

  const dates = [...new Set(items.map((item) => item.date))].sort();
  const hours = Array.from({ length: 24 }, (_, hour) => hour);
  const valueMap = new Map(items.map((item) => [`${item.date}-${item.hour}`, Number(item[valueKey] || 0)]));
  const maxValue = Math.max(...Array.from(valueMap.values()), 1);

  let cells = `<div class="heatmap-label sticky-col sticky-row"></div>${hours.map((hour) => `<div class="heatmap-label sticky-row">${hour}</div>`).join("")}`;
  dates.forEach((date) => {
    cells += `<div class="heatmap-label sticky-col">${escapeHtml(String(date).slice(5))}</div>`;
    hours.forEach((hour) => {
      const value = valueMap.get(`${date}-${hour}`) || 0;
      const display = mode === "rate" ? `${(value * 100).toFixed(0)}%` : formatNumber(value);
      cells += `<div class="heatmap-cell" style="background:${heatColor(value, maxValue, mode)}">${escapeHtml(display)}</div>`;
    });
  });

  container.innerHTML = `<div class="heatmap"><div class="heatmap-grid" style="grid-template-columns: 88px repeat(${hours.length}, minmax(38px, 1fr));">${cells}</div></div>`;
}

export function createSearchableSelect(
  containerSelector,
  { placeholder = "输入关键词搜索", allLabel = "全部", onChange = () => {} } = {},
) {
  const host = $(containerSelector);
  if (!host) return null;

  host.innerHTML = `
    <div class="search-select">
      <div class="search-select-control">
        <input class="search-select-input" type="text" placeholder="${escapeHtml(placeholder)}" autocomplete="off">
        <button type="button" class="search-select-clear" title="清空">×</button>
      </div>
      <div class="search-select-menu" hidden></div>
    </div>
  `;

  const input = host.querySelector(".search-select-input");
  const clear = host.querySelector(".search-select-clear");
  const menu = host.querySelector(".search-select-menu");
  let allOptions = [{ value: "", label: allLabel, searchText: allLabel }];
  let filteredOptions = allOptions.slice();
  let selectedValue = "";
  let isOpen = false;
  let activeIndex = -1;

  const normalize = (value) => String(value ?? "").trim().toLowerCase();
  const optionByValue = (value) => allOptions.find((item) => item.value === value) || allOptions[0];

  function refreshClearButton() {
    clear.hidden = !selectedValue && !input.value;
  }

  function renderMenu() {
    if (!isOpen) {
      menu.hidden = true;
      menu.innerHTML = "";
      return;
    }
    menu.hidden = false;
    if (!filteredOptions.length) {
      menu.innerHTML = '<div class="search-select-empty">没有匹配项</div>';
      return;
    }
    menu.innerHTML = filteredOptions
      .map(
        (item, index) => `
          <button type="button" class="search-select-option ${index === activeIndex ? "active" : ""}" data-value="${escapeHtml(item.value)}">
            ${escapeHtml(item.label)}
          </button>
        `,
      )
      .join("");
  }

  function applyFilter(keyword = "") {
    const normalizedKeyword = normalize(keyword);
    filteredOptions = allOptions.filter((item) => normalize(item.searchText || item.label).includes(normalizedKeyword));
    activeIndex = filteredOptions.length ? 0 : -1;
    renderMenu();
  }

  function commit(value, notify = true) {
    selectedValue = value;
    const selected = optionByValue(value);
    input.value = value ? selected.label : "";
    refreshClearButton();
    isOpen = false;
    renderMenu();
    if (notify) onChange(value, selected);
  }

  input.addEventListener("focus", () => {
    isOpen = true;
    applyFilter(input.value);
  });

  input.addEventListener("input", () => {
    selectedValue = "";
    refreshClearButton();
    isOpen = true;
    applyFilter(input.value);
  });

  input.addEventListener("keydown", (event) => {
    if (!isOpen && ["ArrowDown", "ArrowUp", "Enter"].includes(event.key)) {
      isOpen = true;
      applyFilter(input.value);
    }
    if (!isOpen) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = filteredOptions.length ? (activeIndex + 1) % filteredOptions.length : -1;
      renderMenu();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = filteredOptions.length ? (activeIndex - 1 + filteredOptions.length) % filteredOptions.length : -1;
      renderMenu();
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (filteredOptions[activeIndex]) commit(filteredOptions[activeIndex].value);
    } else if (event.key === "Escape") {
      isOpen = false;
      renderMenu();
    }
  });

  menu.addEventListener("mousedown", (event) => {
    const button = event.target.closest(".search-select-option");
    if (!button) return;
    event.preventDefault();
    commit(button.dataset.value || "");
  });

  clear.addEventListener("click", () => {
    input.value = "";
    commit("");
  });

  document.addEventListener("click", (event) => {
    if (!host.contains(event.target)) {
      isOpen = false;
      renderMenu();
      if (!selectedValue && input.value) {
        const exact = allOptions.find((item) => item.label === input.value);
        if (exact) commit(exact.value);
        else input.value = "";
      }
      refreshClearButton();
    }
  });

  refreshClearButton();

  return {
    setOptions(options) {
      allOptions = [{ value: "", label: allLabel, searchText: allLabel }, ...(options || [])];
      applyFilter(input.value);
    },
    setValue(value, notify = false) {
      commit(value || "", notify);
    },
    getValue() {
      return selectedValue;
    },
  };
}

export function createPartnerRegionFilterController({
  selectors,
  placeholders = {},
  onChange = () => {},
}) {
  const filterKeys = ["province", "city", "district", "partner_id"];
  const defaultPlaceholders = {
    province: "输入省份搜索",
    city: "输入城市搜索",
    district: "输入区县搜索",
    partner_id: "输入合伙人名称或 ID 搜索",
  };
  const state = {
    partners: [],
    filters: { province: "", city: "", district: "", partner_id: "" },
    controls: {},
  };

  function uniqueSorted(values) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "zh-CN"));
  }

  function matchesPartner(partner, ignoreKey = "") {
    if (ignoreKey !== "province" && state.filters.province && partner.province !== state.filters.province) return false;
    if (ignoreKey !== "city" && state.filters.city && partner.city !== state.filters.city) return false;
    if (ignoreKey !== "district" && state.filters.district && partner.district !== state.filters.district) return false;
    if (ignoreKey !== "partner_id" && state.filters.partner_id && partner.partner_id !== state.filters.partner_id) return false;
    return true;
  }

  function buildOptions(ignoreKey = "") {
    const pool = state.partners.filter((partner) => matchesPartner(partner, ignoreKey));
    return {
      province: uniqueSorted(pool.map((item) => item.province)).map((value) => ({ value, label: value, searchText: value })),
      city: uniqueSorted(pool.map((item) => item.city)).map((value) => ({ value, label: value, searchText: value })),
      district: uniqueSorted(pool.map((item) => item.district)).map((value) => ({ value, label: value, searchText: value })),
      partner_id: pool
        .map((item) => ({
          value: item.partner_id,
          label: item.partner_name || item.partner_id,
          searchText: [item.partner_name, item.partner_id, item.province, item.city, item.district].filter(Boolean).join(" "),
        }))
        .sort((a, b) => a.label.localeCompare(b.label, "zh-CN")),
    };
  }

  function reconcileFilters() {
    let options = buildOptions();
    let changed = true;
    while (changed) {
      changed = false;
      filterKeys.forEach((key) => {
        if (!state.filters[key]) return;
        if (!options[key].some((item) => item.value === state.filters[key])) {
          state.filters[key] = "";
          changed = true;
        }
      });
      if (changed) options = buildOptions();
    }
    return options;
  }

  function render() {
    const options = reconcileFilters();
    Object.entries(options).forEach(([key, value]) => {
      state.controls[key].setOptions(value);
      state.controls[key].setValue(state.filters[key], false);
    });
  }

  function handleFilterChange(key, value) {
    state.filters[key] = value;
    render();
    onChange({ ...state.filters });
  }

  function ensureControls() {
    if (state.controls.province) return;
    filterKeys.forEach((key) => {
      state.controls[key] = createSearchableSelect(selectors[key], {
        placeholder: placeholders[key] || defaultPlaceholders[key],
        onChange: (value) => handleFilterChange(key, value),
      });
    });
  }

  ensureControls();

  return {
    get filters() {
      return state.filters;
    },
    setPartners(partners) {
      state.partners = partners || [];
      render();
    },
    render,
  };
}

export function showError(error) {
  console.error(error);
  window.alert(error?.message || "页面加载失败，请稍后重试。");
}
