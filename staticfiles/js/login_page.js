/**
 * 로그인 중복 클릭 방지 및 로딩 표시
 */
document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");
  const loginBtn = document.getElementById("loginBtn");

  if (loginForm && loginBtn) {
    loginForm.addEventListener("submit", function () {
      loginBtn.disabled = true;
      loginBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        로그인 중...
      `;
    });
  } else {
    console.warn("⚠️ loginForm 또는 loginBtn을 찾을 수 없습니다.");
  }
});
