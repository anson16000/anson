import { api } from "/static/core/api.js";
import { MAX_QUERY_DAYS, validateDateRangeBySelectors } from "/static/core/date.js";
import { requireElement, setHtml } from "/static/ui/base.js";

const FILTER_STORAGE_KEY = "dashboard_filters";

export function saveFilters(filters, pageKey = "") {
  try {
    const data = JSON.parse(sessionStorage.getItem(FILTER_STORAGE_KEY) || "{}");
    if (pageKey) {
      data[pageKey] = filters;
    } else {
      Object.assign(data, filters);
    }
    sessionStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn("保存筛选条件失败", e);
  }
}

export function loadFilters(pageKey = "") {
  try {
    const data = JSON.parse(sessionStorage.getItem(FILTER_STORAGE_KEY) || "{}");
    return pageKey ? (data[pageKey] || {}) : data;
  } catch (e) {
    return {};
  }
}

export function clearFilters(pageKey = "") {
  try {
    if (pageKey) {
      const data = JSON.parse(sessionStorage.getItem(FILTER_STORAGE_KEY) || "{}");
      delete data[pageKey];
      sessionStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(data));
    } else {
      sessionStorage.removeItem(FILTER_STORAGE_KEY);
    }
  } catch (e) {
    console.warn("清除筛选条件失败", e);
  }
}

export function renderFilterSummary(selector, filters, labelMap = {}) {
  const tags = [];
  if (filters.start_date && filters.end_date) {
    tags.push(`<span class="filter-tag"><span class="filter-tag-label">日期</span>${filters.start_date} 至 ${filters.end_date}</span>`);
  }
  Object.entries(filters).forEach(([key, value]) => {
    if (!value || ["start_date", "end_date"].includes(key)) return;
    const label = labelMap[key] || key;
    tags.push(`<span class="filter-tag"><span class="filter-tag-label">${label}</span>${value}</span>`);
  });
  setHtml(selector, tags.join(""));
}

export function createPageController(config) {
  const state = {
    ...(config.initialState || {}),
  };

  function getBaseFilters() {
    const { startDateText, endDateText } = validateDateRangeBySelectors(
      config.selectors.startDate,
      config.selectors.endDate,
      config.maxDays || MAX_QUERY_DAYS,
    );

    return {
      start_date: startDateText,
      end_date: endDateText,
      ...(config.additionalFilters ? config.additionalFilters(state) : {}),
    };
  }

  async function loadPage() {
    const filters = getBaseFilters();
    config.onSaveFilters?.(filters);
    if (config.requireField) {
      const requiredValue = filters[config.requireField];
      if (!requiredValue) {
        config.clearPanels?.(state);
        return;
      }
    }
    await config.loadData(filters, state);
  }

  function bindRefresh(selector) {
    requireElement(selector).addEventListener("click", () => loadPage().catch(config.onError));
  }

  function bindChange(selectors) {
    selectors.forEach((selector) => {
      requireElement(selector).addEventListener("change", () => loadPage().catch(config.onError));
    });
  }

  async function bootstrap() {
    config.clearPanels?.(state);
    const meta = await api("/api/v1/meta");
    await config.populateFilters?.(meta, state);
    config.bindEvents?.({ loadPage, bindRefresh, bindChange, state });
    if (config.autoLoad !== false) {
      await loadPage();
    }
  }

  return { state, bootstrap, loadPage, getBaseFilters };
}
