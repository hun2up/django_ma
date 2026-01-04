// django_ma/static/js/board/form_submit_lock.js
/**
 * Board Form Common JS (FINAL)
 * - post/task create/edit 공용
 * - submit 중복 방지(잠금 + 스피너)
 * - file_upload_utils.js initFileUpload 자동 초기화까지 흡수
 *
 * 전제:
 * - 폼 id: #postForm 또는 #taskForm (둘 중 하나)
 * - submit 버튼 id: #submitBtn (권장)
 * - 파일 업로드 DOM(권장):
 *   - input[type=file]#fileInput name="attachments" multiple
 *   - 기존 파일 삭제 버튼: .remove-existing (data-id)
 *   - 삭제 hidden container: #deleteContainer
 */

(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function initSubmitLock(form) {
    const submitBtn =
      qs("#submitBtn", form) || qs('button[type="submit"]', form);

    form.addEventListener("submit", function (e) {
      if (form.dataset.submitting === "1") {
        e.preventDefault();
        alert("처리 중입니다.\n잠시만 기다려주세요.");
        return;
      }
      form.dataset.submitting = "1";

      if (submitBtn) {
        submitBtn.disabled = true;
        if (!submitBtn.dataset.prevHtml) {
          submitBtn.dataset.prevHtml = submitBtn.innerHTML;
        }
        submitBtn.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> 처리 중...';
        submitBtn.style.opacity = "0.7";
        submitBtn.style.cursor = "not-allowed";
      }
    });
  }

  function initFileUploadIfPossible(form) {
    // file_upload_utils.js의 initFileUpload가 로드된 경우에만 실행
    if (typeof window.initFileUpload !== "function") return;

    const hasFileInput =
      !!qs('#fileInput[type="file"]', form) ||
      !!qs('input[type="file"][name="attachments"]', form);
    const deleteContainer = qs("#deleteContainer", form);
    const existingRemoveBtn = qs(".remove-existing", form);

    // 파일 UI가 없는 폼에서는 아무 것도 하지 않음(안전)
    if (!hasFileInput || !deleteContainer) return;

    window.initFileUpload({
      // formSelector는 selector 문자열을 기대하므로 id 기반으로 결정
      formSelector: form.id ? `#${form.id}` : null,
      existingFileSelector: ".remove-existing",
      deleteContainerSelector: "#deleteContainer",
      maxFileSize: 10 * 1024 * 1024, // 10MB
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const form = qs("#postForm") || qs("#taskForm");
    if (!form) return;

    initSubmitLock(form);
    initFileUploadIfPossible(form);
  });
})();
