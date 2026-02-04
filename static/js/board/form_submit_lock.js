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
// ✅ 중요(버그픽스)
// - file_upload_utils가 submit을 preventDefault() 할 수 있으므로
//   1) initFileUpload를 먼저 실행하고
//   2) submit 이벤트에서 e.defaultPrevented면 잠금을 걸지 않음
// - 그렇지 않으면 "처리 중..." 무한 로딩처럼 보일 수 있음
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
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

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

  function ensureDeleteContainer(form) {
    if (!form) return null;

    let el = qs("#deleteContainer", form);
    if (el) return el;

    // create 화면에는 deleteContainer가 없을 수 있으므로 자동 생성
    el = document.createElement("div");
    el.id = "deleteContainer";
    el.className = "d-none";
    form.appendChild(el);
    return el;
  }

  function hasFileInput(form) {
    if (!form) return false;
    return (
      !!qs('#fileInput[type="file"]', form) ||
      !!qs('input[type="file"][name="attachments"]', form)
    );
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

  function unlockSubmitButton(btn) {
    if (!btn) return;

    btn.disabled = false;
    btn.classList.remove("is-busy");

    if (btn.dataset.prevHtml) {
      btn.innerHTML = btn.dataset.prevHtml;
    }
  }

  function initSubmitLock(form) {
    const submitBtn = findSubmitBtn(form);
    if (!submitBtn) return;

    // 중복 바인딩 방지(템플릿 include/partial 중복 대비)
    if (form.dataset.submitLockBound === "1") return;
    form.dataset.submitLockBound = "1";

    form.addEventListener("submit", (e) => {
      // ✅ file_upload_utils 등 다른 로직이 제출을 막은 경우:
      // 잠금을 걸면 "처리 중..." 상태로 남아 무한 로딩처럼 보일 수 있음
      if (e.defaultPrevented) return;

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

    // 파일 업로드 UI가 없으면 조용히 종료
    if (!hasFileInput(form)) return;

    // deleteContainer 보장
    ensureDeleteContainer(form);

    // formSelector 필요(유틸이 selector 기반이므로)
    const formSelector = form.id ? `#${form.id}` : null;
    if (!formSelector) return;

    window.initFileUpload({
      formSelector,
      existingFileSelector: ".remove-existing",
      deleteContainerSelector: "#deleteContainer",
      maxFileSize: MAX_FILE_SIZE,
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

    // ✅ 중요: file_upload_utils가 submit을 막을 수 있으므로 먼저 초기화
    initFileUploadIfPossible(form);

    // ✅ 그 다음 submit lock 바인딩( defaultPrevented 감지 가능 )
    initSubmitLock(form);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  /* =========================================================
   * 4) BFCache restore (뒤로가기/앞으로가기)
   * ========================================================= */
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;

    // 전역 init 플래그 해제 → 재부팅
    document.body.dataset[INIT_FLAG] = "0";

    // 폼 상태 초기화 + 버튼 원복
    const form = findForm();
    if (form) {
      form.dataset.submitLockBound = "0";
      form.dataset.submitting = "0";

      const btn = findSubmitBtn(form);
      unlockSubmitButton(btn);
    }

    boot();
  });
})();
