// django_ma/static/js/partner/manage_efficiency/col_widths.js
//
// ✅ inputTable column widths via ratio config (percent)
// - reads root.dataset.inputColWidths (json)
// - normalizes ratios and applies to <colgroup><col data-col="...">
// - optional min widths (px) support

function str(v) {
  return String(v ?? "").trim();
}

function safeJsonParse(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function normalizeRatios(map) {
  const entries = Object.entries(map || {}).filter(([k, v]) => Number(v) > 0);
  const sum = entries.reduce((a, [, v]) => a + Number(v), 0);
  if (!sum) return {};
  const out = {};
  for (const [k, v] of entries) out[k] = (Number(v) / sum) * 100;
  return out;
}

/**
 * @param {HTMLElement} root - #manage-efficiency
 * @param {HTMLTableElement} table - #inputTable
 */
export function applyInputColWidths(root, table) {
  if (!root || !table) return;

  const raw = str(root.dataset.inputColWidths || "");
  if (!raw) return;

  const conf = safeJsonParse(raw);
  if (!conf || typeof conf !== "object") return;

  const ratios = normalizeRatios(conf);

  const cols = table.querySelectorAll("colgroup col[data-col]");
  if (!cols.length) return;

  cols.forEach((col) => {
    const key = str(col.dataset.col);
    const w = ratios[key];
    if (!w) return;
    col.style.width = `${w}%`;
  });

  // ✅ table-layout fixed가 colgroup 폭을 가장 잘 지켜줌
  table.style.tableLayout = "fixed";
}
