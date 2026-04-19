import { createSearchableSelect } from "/static/ui/select.js";

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
