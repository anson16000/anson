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

export function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

export function formatPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

export function formatMoney(value) {
  return `￥${new Intl.NumberFormat("zh-CN", {
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

export function showError(error) {
  console.error(error);
  window.alert(error?.message || "页面加载失败，请稍后重试。");
}
