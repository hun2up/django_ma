// static/js/partner/manage_structure/utils.js

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

export function alertBox(msg) {
  // 그냥 alert로
  window.alert(msg);
}

export function getCSRFToken() {
  return (
    window.csrfToken ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    ""
  );
}

export function pad2(n) {
  n = Number(n);
  return n < 10 ? "0" + n : String(n);
}
