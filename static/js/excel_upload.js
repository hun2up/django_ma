/**
 * django_ma/static/js/excel_upload.js (FINAL REFACTOR)
 * -----------------------------------------------------------------------------
 * ✅ 엑셀 업로드 버튼/파일선택/업로드 실행
 * - ✅ CSRF 헤더 추가 (Django 403 방지)
 * - ✅ same-origin credentials 추가
 * - ✅ submit 중복 방지
 * - (참고) 업로드 후 reload 유지
 */
document.addEventListener("DOMContentLoaded", function () {
  const uploadForm = document.getElementById("excelUploadForm");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("excelFile");

  if (!uploadForm || !uploadBtn || !fileInput) return;

  // (선택) DataTables 사용 중이라도 업로드 후 reload 정책이므로 굳이 참조하지 않음
  // const dt = window.jQuery?.fn?.DataTable ? window.jQuery("#mainTable").DataTable() : null;

  const getCSRF = () =>
    document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    "";

  uploadBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async () => {
    if (!fileInput.files.length) return;

    const fileName = fileInput.files[0].name || "선택한 파일";
    const ok = confirm(`"${fileName}" 파일을 업로드하시겠습니까?`);
    if (!ok) {
      fileInput.value = "";
      return;
    }

    if (uploadForm.dataset.submitting === "1") return;
    uploadForm.dataset.submitting = "1";

    try {
      const formData = new FormData(uploadForm);
      const res = await fetch(uploadForm.action, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": getCSRF(), "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await res.text(); // 서버가 HTML/JSON 무엇을 주든 안전

      alert("엑셀 업로드가 완료되었습니다.");
      location.reload();
    } catch (err) {
      console.error(err);
      alert("업로드 중 오류가 발생했습니다.");
      uploadForm.dataset.submitting = "0";
    }
  });
});
