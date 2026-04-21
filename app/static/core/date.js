import { requireElement } from "/static/ui/base.js";

export const MAX_QUERY_DAYS = 31;

function toDateOnly(value) {
  return value ? new Date(`${value}T00:00:00`) : null;
}

export function setDateRange(startSelector, endSelector, latestDate) {
  const startInput = requireElement(startSelector);
  const endInput = requireElement(endSelector);
  if (!latestDate) return;
  endInput.value = latestDate;
  if (!startInput.value) {
    startInput.value = latestDate;
  }
}

export function validateDateRange(startValue, endValue, maxDays = MAX_QUERY_DAYS) {
  if (!startValue || !endValue) {
    throw new Error("请选择开始日期和结束日期。");
  }

  const startDate = toDateOnly(startValue);
  const endDate = toDateOnly(endValue);
  if (!startDate || !endDate || Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
    throw new Error("日期格式无效，请重新选择。");
  }
  if (startDate > endDate) {
    throw new Error("开始日期不能晚于结束日期。");
  }

  const diffDays = Math.floor((endDate - startDate) / 86400000) + 1;
  if (diffDays > maxDays) {
    throw new Error(`单次查询最多支持 ${maxDays} 天，请缩小日期范围。`);
  }

  return {
    startDateText: startValue,
    endDateText: endValue,
    diffDays,
  };
}

export function validateDateRangeBySelectors(startSelector, endSelector, maxDays = MAX_QUERY_DAYS) {
  const startInput = requireElement(startSelector);
  const endInput = requireElement(endSelector);
  return validateDateRange(startInput.value, endInput.value, maxDays);
}

function toDateOnlyStr(baseDate, offsetDays) {
  const d = new Date(`${baseDate}T00:00:00`);
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function addDateShortcuts(startSelector, endSelector, latestDate) {
  if (!latestDate) return;
  const startInput = requireElement(startSelector);
  const endInput = requireElement(endSelector);
  const parentLabel = startInput.closest("label.field");
  if (!parentLabel?.parentElement) return;

  const existing = parentLabel.parentElement.querySelector(".date-shortcuts");
  if (existing) return;

  const shortcuts = [
    { label: "今天", days: 0 },
    { label: "昨天", days: 1 },
    { label: "近7天", days: 6 },
    { label: "近30天", days: 29 },
  ];

  const container = document.createElement("div");
  container.className = "date-shortcuts";

  const buttons = shortcuts.map(({ label, days }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "date-shortcut-btn";
    btn.textContent = label;
    btn.dataset.days = String(days);
    btn.addEventListener("click", () => {
      const end = latestDate;
      const start = days === 0 ? latestDate : toDateOnlyStr(latestDate, -days);
      startInput.value = start;
      endInput.value = end;
      buttons.forEach((item) => item.classList.toggle("active", item === btn));
      startInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    container.appendChild(btn);
    return btn;
  });

  parentLabel.parentElement.insertBefore(container, parentLabel);

  requestAnimationFrame(() => {
    const sv = startInput.value;
    const ev = endInput.value;
    if (!sv || !ev) return;
    const diff = Math.floor((toDateOnly(ev) - toDateOnly(sv)) / 86400000);
    const match = buttons.find((item) => Number(item.dataset.days) === diff);
    if (match) match.classList.add("active");
  });
}
