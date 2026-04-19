import { api } from "/static/core/api.js";
import { MAX_QUERY_DAYS, validateDateRangeBySelectors } from "/static/core/date.js";
import { requireElement } from "/static/ui/base.js";

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
