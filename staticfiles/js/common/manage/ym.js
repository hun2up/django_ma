/**
 * django_ma/static/js/common/manage/ym.js
 * ------------------------------------------------------------
 * - YYYY-MM 관련 공통 유틸
 * - pad2, selectedYM, normalizeYM
 * ------------------------------------------------------------
 */

export function pad2(n) {
  const num = Number(n);
  return num < 10 ? "0" + num : String(num);
}

export function selectedYM(yearSelectEl, monthSelectEl) {
  const y = yearSelectEl?.value;
  const m = monthSelectEl?.value;
  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}

export function normalizeYM(ym) {
  const s = String(ym || "").trim();
  if (!s) return "";

  if (/^\d{4}-\d{2}$/.test(s)) return s;

  const digits = s.replaceAll("-", "").replaceAll("/", "").replaceAll(".", "");
  if (/^\d{6}$/.test(digits)) return `${digits.slice(0, 4)}-${digits.slice(4, 6)}`;

  if (s.length >= 6) return `${s.slice(0, 4)}-${s.slice(-2)}`;
  return s;
}
