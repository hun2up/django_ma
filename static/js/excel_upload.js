// ✅ excel_upload.js — 엑셀 업로드 + 테이블 자동 새로고침
document.addEventListener("DOMContentLoaded", function() {
  const uploadForm = document.getElementById("excelUploadForm");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("excelFile");
  const table = $("#mainTable").DataTable ? $("#mainTable").DataTable() : null;

  if (!uploadForm || !uploadBtn || !fileInput) return;

  uploadBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    if (!fileInput.files.length) return;
    const fileName = fileInput.files[0].name;
    if (confirm(`"${fileName}" 파일을 업로드하시겠습니까?`)) {
      const formData = new FormData(uploadForm);
      fetch(uploadForm.action, {
        method: "POST",
        body: formData,
      })
      .then(res => res.text())
      .then(() => {
        alert("엑셀 업로드가 완료되었습니다.");
        location.reload(); // ✅ 업로드 후 즉시 테이블 갱신
      })
      .catch(err => {
        console.error(err);
        alert("업로드 중 오류가 발생했습니다.");
      });
    } else {
      fileInput.value = "";
    }
  });
});
