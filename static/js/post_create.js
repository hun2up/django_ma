/**
 * post_create.js — 게시글 작성 중복 클릭 방지
 */
document.addEventListener("DOMContentLoaded", function() {
  const form = document.getElementById("postForm");
  const submitBtn = document.getElementById("submitBtn");

  if (!form || !submitBtn) return;

  form.addEventListener("submit", function(e) {
    if (submitBtn.disabled) {
      e.preventDefault();
      alert("처리 중입니다.\n잠시만 기다려주세요.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> 처리 중...';
    submitBtn.style.opacity = "0.7";
    submitBtn.style.cursor = "not-allowed";
  });
});
