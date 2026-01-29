/**
 * django_ma/static/js/login_page.js (FINAL)
 * -----------------------------------------------------------------------------
 * ✅ 로그인 중복 클릭 방지 + 로딩 표시
 */
document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");
  const loginBtn = document.getElementById("loginBtn");

  if (!loginForm || !loginBtn) {
    console.warn("⚠️ loginForm 또는 loginBtn을 찾을 수 없습니다.");
    return;
  }

  loginForm.addEventListener("submit", function () {
    if (loginForm.dataset.submitting === "1") return;
    loginForm.dataset.submitting = "1";

    loginBtn.disabled = true;
    loginBtn.innerHTML = `
      <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
      로그인 중...
    `;
  });
});
