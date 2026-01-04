// django_ma/static/js/partner/manage_efficiency/utils.js

import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { getCSRFToken } from "../../common/manage/csrf.js";
import { pad2 } from "../../common/manage/ym.js";

export { showLoading, hideLoading, getCSRFToken, pad2 };

export function alertBox(msg) {
  window.alert(msg);
}

export function selectedYM(yearEl, monthEl) {
  const yEl = yearEl || document.getElementById("yearSelect");
  const mEl = monthEl || document.getElementById("monthSelect");

  const y = String(yEl?.value ?? "").trim();
  const m = String(mEl?.value ?? "").trim();

  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}
