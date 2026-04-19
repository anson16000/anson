import { $, escapeHtml } from "/static/ui/base.js";

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
  const optionByValue = (value) => allOptions.find((item) => String(item.value) === String(value)) || allOptions[0];

  function findExactOption(rawValue) {
    const normalizedValue = normalize(rawValue);
    if (!normalizedValue) return null;
    return (
      allOptions.find((item) => normalize(item.label) === normalizedValue)
      || allOptions.find((item) => normalize(item.value) === normalizedValue)
      || null
    );
  }

  function findSingleFilteredOption(rawValue) {
    const normalizedValue = normalize(rawValue);
    if (!normalizedValue || filteredOptions.length !== 1) return null;
    const [onlyOption] = filteredOptions;
    if (!onlyOption) return null;
    if (
      normalize(onlyOption.label).includes(normalizedValue)
      || normalize(onlyOption.value).includes(normalizedValue)
      || normalize(onlyOption.searchText || onlyOption.label).includes(normalizedValue)
    ) {
      return onlyOption;
    }
    return null;
  }

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

  function commitFromInput() {
    if (selectedValue) return true;
    const exact = findExactOption(input.value);
    if (exact) {
      commit(exact.value);
      return true;
    }
    const single = findSingleFilteredOption(input.value);
    if (single) {
      commit(single.value);
      return true;
    }
    return false;
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

  input.addEventListener("blur", () => {
    window.setTimeout(() => {
      if (document.activeElement && host.contains(document.activeElement)) return;
      if (!commitFromInput()) {
        input.value = selectedValue ? optionByValue(selectedValue).label : "";
        isOpen = false;
        renderMenu();
        refreshClearButton();
      }
    }, 0);
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
      if (filteredOptions[activeIndex]) {
        commit(filteredOptions[activeIndex].value);
      } else if (!commitFromInput()) {
        input.select();
      }
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
      if (!commitFromInput()) {
        input.value = selectedValue ? optionByValue(selectedValue).label : "";
      }
      isOpen = false;
      renderMenu();
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
