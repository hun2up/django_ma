/**
 * django_ma/static/js/common/manage/datatables.js
 * ------------------------------------------------------------
 * - DataTables 존재 여부 체크
 * - 안전 destroy / adjust
 * - "페이지별 DT 초기화"에만 사용
 * ------------------------------------------------------------
 */

export function canUseDataTables(tableEl) {
  return !!(tableEl && window.jQuery && window.jQuery.fn?.DataTable);
}

export function destroyDataTableIfExists(tableEl) {
  try {
    if (tableEl && window.jQuery?.fn?.DataTable?.isDataTable?.(tableEl)) {
      window.jQuery(tableEl).DataTable().clear().destroy();
    }
  } catch (_) {}
}

export function safeAdjust(dt) {
  if (!dt) return;
  try {
    dt.columns.adjust().draw(false);
  } catch (_) {}
}
