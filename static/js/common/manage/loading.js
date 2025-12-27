/**
 * django_ma/static/js/common/manage/loading.js
 * ------------------------------------------------------------
 * - loadingOverlay 공통 제어
 * ------------------------------------------------------------
 */

export function showLoading(msg = "처리 중...") {
  const overlay = document.getElementById("loadingOverlay");
  if (!overlay) return;
  const label = overlay.querySelector(".mt-2");
  if (label) label.textContent = msg;
  overlay.hidden = false;
}

export function hideLoading() {
  const overlay = document.getElementById("loadingOverlay");
  if (!overlay) return;
  overlay.hidden = true;
}
