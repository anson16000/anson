import { $, requireElement } from "/static/ui/base.js";

export const MAX_QUERY_DAYS = 31;

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

export function validateDateRange(startDateText, endDateText, maxDays = MAX_QUERY_DAYS) {
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

export function validateDateRangeBySelectors(startSelector, endSelector, maxDays = MAX_QUERY_DAYS) {
  return validateDateRange(
    requireElement(startSelector, "开始日期").value,
    requireElement(endSelector, "结束日期").value,
    maxDays,
  );
}
