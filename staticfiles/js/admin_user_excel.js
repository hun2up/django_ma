/**
 * django_ma/static/js/admin_user_excel.js (FINAL REFACTOR)
 * -----------------------------------------------------------------------------
 * ✅ 엑셀 업로드 폼: submit 중복 클릭 방지
 * - form 존재 여부 가드
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("excelUploadForm");
  if (!form) return;

  form.addEventListener("submit", () => {
    if (form.dataset.submitting === "1") return;
    form.dataset.submitting = "1";

    const btn = form.querySelector("button[type='submit']");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "업로드 중...";
    }
  });
});
