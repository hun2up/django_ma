// django_ma/static/js/partner/manage_structure/utils.js
import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2 } from "../../common/manage/ym.js";

/**
 * ✅ 기존 코드 호환 레이어 (SSOT)
 * - fetch/save/input_rows 등에서 같은 유틸을 공유
 */
export { showLoading, hideLoading, getCSRFToken, pad2 };

export function alertBox(msg) {
  window.alert(msg);
}

/** 선택 YM (year/month select → YYYY-MM) */
export function selectedYM(yearEl, monthEl) {
  const y = String(yearEl?.value ?? "").trim();
  const m = String(monthEl?.value ?? "").trim();
  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}
