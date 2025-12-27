/**
 * django_ma/static/js/common/manage/dataset.js
 * ------------------------------------------------------------
 * - dataset key 접근 헬퍼
 * - 여러 key 후보 중 첫 번째 유효값 반환
 * - 공통 ds() 제공
 * ------------------------------------------------------------
 */

export function ds(rootEl, key, fallback = "") {
  try {
    return (rootEl?.dataset?.[key] ?? fallback).toString().trim();
  } catch {
    return (fallback ?? "").toString().trim();
  }
}

export function getDatasetUrl(rootEl, keys = []) {
  const dsObj = rootEl?.dataset;
  if (!dsObj) return "";
  for (const k of keys) {
    const v = dsObj[k];
    if (v && String(v).trim()) return String(v).trim();
  }
  return "";
}
