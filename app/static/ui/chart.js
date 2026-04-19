import { $, escapeHtml, formatNumber } from "/static/ui/base.js";

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
