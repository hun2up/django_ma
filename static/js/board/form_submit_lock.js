// django_ma/static/js/board/form_submit_lock.js
// =========================================================
// Board Form Submit Lock (post/task create/edit 공용)
//
// ✅ 주요 기능
// - submit 중복 방지(잠금 + 스피너 + 버튼 비활성화)
// - file_upload_utils.js의 initFileUpload가 있으면 자동 초기화
//
// ✅ base.css 모듈화 반영
// - 인라인 style 제거 → .is-busy(전역 유틸) + disabled 사용
//
// ✅ 전제(권장)
// - 폼 id: #postForm 또는 #taskForm
// - submit 버튼 id: #submitBtn (없으면 form 내 submit 버튼 fallback)
// - 파일 업로드 UI(있을 때만 initFileUpload 실행)
//   - input[type=file]#fileInput 또는 name="attachments"
//   - 삭제 hidden container: #deleteContainer
// =========================================================

(function () {
  "use strict";

  const INIT_FLAG = "__boardFormSubmitLockInited";

  /* =========================================================
   * 0) DOM helpers
   * ========================================================= */
  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function findForm() {
    return qs("#postForm") || qs("#taskForm");
  }

  function findSubmitBtn(form) {
    if (!form) return null;
    return qs("#submitBtn", form) || qs('button[type="submit"]', form);
  }

  /* =========================================================
   * 1) Submit lock UI
   * ========================================================= */
  function lockSubmitButton(btn) {
    if (!btn) return;

    // 원본 HTML 1회 저장
    if (!btn.dataset.prevHtml) btn.dataset.prevHtml = btn.innerHTML;

    btn.disabled = true;
    btn.classList.add("is-busy"); // ✅ base.css 유틸(인라인 제거)

    btn.innerHTML =
      '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
      "처리 중...";
  }

  function initSubmitLock(form) {
    const submitBtn = findSubmitBtn(form);
    if (!submitBtn) return;

    // 중복 바인딩 방지(템플릿 include/partial 중복 대비)
    if (form.dataset.submitLockBound === "1") return;
    form.dataset.submitLockBound = "1";

    form.addEventListener("submit", (e) => {
      // 이미 submitting이면 중복 제출 차단
      if (form.dataset.submitting === "1") {
        e.preventDefault();
        alert("처리 중입니다.\n잠시만 기다려주세요.");
        return;
      }

      form.dataset.submitting = "1";
      lockSubmitButton(submitBtn);
    });
  }

  /* =========================================================
   * 2) File upload utils bootstrap (optional)
   * ========================================================= */
  function initFileUploadIfPossible(form) {
    // file_upload_utils.js에서 initFileUpload 제공 시에만 실행
    if (typeof window.initFileUpload !== "function") return;
    if (!form) return;

    // 파일 입력 존재 여부(둘 중 하나만 있어도 OK)
    const hasFileInput =
      !!qs('#fileInput[type="file"]', form) ||
      !!qs('input[type="file"][name="attachments"]', form);

    if (!hasFileInput) return;

    // create 화면에는 deleteContainer가 없을 수 있으므로 자동 생성
    let deleteContainer = qs("#deleteContainer", form);
    if (!deleteContainer) {
      deleteContainer = document.createElement("div");
      deleteContainer.id = "deleteContainer";
      deleteContainer.className = "d-none";
      form.appendChild(deleteContainer);
    }

    // formSelector 필요(유틸이 selector 기반이므로)
    const formSelector = form.id ? `#${form.id}` : null;
    if (!formSelector) return;

    window.initFileUpload({
      formSelector,
      existingFileSelector: ".remove-existing",
      deleteContainerSelector: "#deleteContainer",
      maxFileSize: 10 * 1024 * 1024, // 10MB
    });
  }

  /* =========================================================
   * 3) Boot
   * ========================================================= */
  function boot() {
    // BFCache/중복 include 대비 전역 1회 가드
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

  // ✅ BFCache 복원 시 재초기화(특히 뒤로가기)
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    document.body.dataset[INIT_FLAG] = "0";
    const form = findForm();
    if (form) {
      form.dataset.submitLockBound = "0";
      form.dataset.submitting = "0";
    }
    boot();
  });
})();
