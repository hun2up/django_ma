// django_ma/static/js/partner/manage_rate/utils.js
// ======================================================
// ✅ Compatibility layer
// - Keep exported signatures unchanged
// - Delegate to common/manage modules
// ======================================================

import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2, selectedYM } from "../../common/manage/ym.js";

export { showLoading, hideLoading, getCSRFToken, pad2, selectedYM };

export function alertBox(msg) {
  window.alert(msg);
}
