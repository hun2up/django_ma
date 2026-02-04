// django_ma/static/js/partner/manage_structure/utils.js
// ------------------------------------------------------
// ✅ manage_structure 전용 유틸 (호환 레이어)
// - 공용(common/manage/*) 유틸을 재-export 하여 SSOT 유지
// - fetch/save/input_rows 등 동일 유틸을 공유
// ------------------------------------------------------

import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2 } from "../../common/manage/ym.js";

export { showLoading, hideLoading, getCSRFToken, pad2 };

export function alertBox(msg) {
  window.alert(msg);
}

/** year/month select → YYYY-MM */
export function selectedYM(yearEl, monthEl) {
  const y = String(yearEl?.value ?? "").trim();
  const m = String(monthEl?.value ?? "").trim();
  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}
