// django_ma/static/js/partner/manage_efficiency/utils.js

import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2 } from "../../common/manage/ym.js";

/**
 * ✅ 기존 코드 호환 레이어
 * - export 시그니처 유지
 */

export { showLoading, hideLoading };

export function alertBox(msg) {
  window.alert(msg);
}

export { getCSRFToken, pad2 };
