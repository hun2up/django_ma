// django_ma/static/js/task_create.js
// ✅ 직원업무 작성/수정 공용 JS: 중복 제출 방지

document.addEventListener("DOMContentLoaded", () => {
  const form =
    document.querySelector("#taskForm") ||
    document.querySelector("#postForm"); // 혹시 재사용 대비

  if (!form) return;

  const submitBtn =
    form.querySelector("#submitBtn") || form.querySelector('button[type="submit"]');

  form.addEventListener("submit", (e) => {
    if (form.dataset.submitting === "1") {
      e.preventDefault();
      return;
    }
    form.dataset.submitting = "1";

    if (submitBtn) {
      submitBtn.disabled = true;

      // 버튼 텍스트 보존 후 스피너
      const prevText = submitBtn.innerHTML;
      submitBtn.dataset.prevText = prevText;

      submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        처리중...
      `;
    }
  });
});
