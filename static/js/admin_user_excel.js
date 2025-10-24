document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("excelUploadForm");

  form.addEventListener("submit", () => {
    const btn = form.querySelector("button[type='submit']");
    btn.disabled = true;
    btn.textContent = "업로드 중...";
  });
});
