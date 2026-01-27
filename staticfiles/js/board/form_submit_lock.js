// django_ma/static/js/board/form_submit_lock.js
// =========================================================
// Board Form Common JS (post/task create/edit 공용)
//
// ✅ 주요 기능
// - submit 중복 방지(잠금 + 스피너 + 버튼 비활성화)
// - file_upload_utils.js의 initFileUpload가 있으면 자동 초기화
//
// ✅ 권한 전제
// - board 접근은 서버에서(superuser/head/leader) 제한
// - task(create/edit)는 서버에서(superuser)만 접근 가능
// - JS에서는 권한을 막지 않고, DOM이 없으면 조용히 종료
//
// ✅ 전제(권장)
// - 폼 id: #postForm 또는 #taskForm
// - submit 버튼 id: #submitBtn (없으면 form 내 submit 버튼 첫 번째로 fallback)
// - 파일 업로드 UI(있을 때만 initFileUpload 실행)
//   - input[type=file]#fileInput 또는 name="attachments"
//   - 삭제 hidden container: #deleteContainer
// =========================================================

(function () {
  "use strict";

  const INIT_FLAG = "__boardFormSubmitLockInited";

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function findForm() {
    return qs("#postForm") || qs("#taskForm");
  }

  function findSubmitBtn(form) {
    return qs("#submitBtn", form) || qs('button[type="submit"]', form);
  }

  function lockSubmitButton(btn) {
    if (!btn) return;

    btn.disabled = true;

    // 원본 HTML 1회만 저장
    if (!btn.dataset.prevHtml) btn.dataset.prevHtml = btn.innerHTML;

    btn.innerHTML =
      '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> 처리 중...';

    btn.style.opacity = "0.7";
    btn.style.cursor = "not-allowed";
  }

  function initSubmitLock(form) {
    const submitBtn = findSubmitBtn(form);

    form.addEventListener("submit", (e) => {
      if (form.dataset.submitting === "1") {
        e.preventDefault();
        alert("처리 중입니다.\n잠시만 기다려주세요.");
        return;
      }

      form.dataset.submitting = "1";
      lockSubmitButton(submitBtn);
    });
  }

  function initFileUploadIfPossible(form) {
    // file_upload_utils.js에서 initFileUpload 제공 시에만 실행
    if (typeof window.initFileUpload !== "function") return;

    const hasFileInput =
      !!qs('#fileInput[type="file"]', form) ||
      !!qs('input[type="file"][name="attachments"]', form);

    const deleteContainer = qs("#deleteContainer", form);

    // 파일 UI가 없는 폼은 그대로 종료
    if (!hasFileInput || !deleteContainer) return;

    const formSelector = form.id ? `#${form.id}` : null;
    if (!formSelector) return;

    window.initFileUpload({
      formSelector,
      existingFileSelector: ".remove-existing",
      deleteContainerSelector: "#deleteContainer",
      maxFileSize: 10 * 1024 * 1024, // 10MB
    });
  }

  function boot() {
    // 중복 초기화 방지(BFCache/중복 include 대비)
    if (document.body.dataset[INIT_FLAG] === "1") return;
    document.body.dataset[INIT_FLAG] = "1";

    const form = findForm();
    if (!form) return;

    initSubmitLock(form);
    initFileUploadIfPossible(form);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
