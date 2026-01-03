// django_ma/static/js/partner/manage_efficiency/utils.js

import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2 } from "../../common/manage/ym.js";

/**
 * ✅ 기존 코드 호환 레이어 (manage_efficiency 전용)
 * - 다른 모듈(confirm_upload.js, save.js, fetch.js 등)에서 기대하는 export 유지
 */

export { showLoading, hideLoading, getCSRFToken, pad2 };

export function alertBox(msg) {
  window.alert(msg);
}

/**
 * ✅ "YYYY-MM" 생성 헬퍼
 * - yearEl/monthEl을 넘기면 그대로 사용
 * - 없으면 id 기반 fallback 사용
 */
export function selectedYM(yearEl, monthEl) {
  const yEl = yearEl || document.getElementById("yearSelect");
  const mEl = monthEl || document.getElementById("monthSelect");

  const y = String(yEl?.value ?? "").trim();
  const m = String(mEl?.value ?? "").trim();

  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}
