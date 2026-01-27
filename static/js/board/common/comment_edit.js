// django_ma/static/js/board/common/comment_edit.js
// =========================================================
// Board Common Comment Inline Edit (post_detail / task_detail 공용)
//
// ✅ 주요 기능
// - .edit-comment-btn 클릭 시 해당 댓글을 textarea 인라인 편집 모드로 전환
// - 저장은 기존 폼 POST 흐름을 그대로 사용(action_type=edit_comment)
// - 취소 시 원문 복구(새로고침 없음)
// - CSRF: #commentEditCsrfToken 우선 → 없으면 페이지 내 csrf input fallback
//
// ✅ 권한 전제
// - board 앱 접근 자체는 서버에서 (superuser/head/leader)로 제한
// - task_detail은 superuser만 접근 가능 (서버에서 제한)
// - 따라서 JS는 권한검증을 하지 않으며, DOM/토큰 미존재 시 안전 종료
//
// ✅ 템플릿 전제(권장)
// - <input type="hidden" id="commentEditCsrfToken" value="{{ csrf_token }}">
// - 댓글 컨테이너: .comment-content (권장: data-comment-id 포함)
// - 수정 버튼: .edit-comment-btn[data-id]
// - 버튼 그룹: .edit-delete-btns
// - 본문: p.comment-text
// =========================================================

(function () {
  "use strict";

  const NS = (window.Board = window.Board || {});
  NS.Common = NS.Common || {};

  const INIT_FLAG = "__boardCommentEditInited";

  /* -----------------------------
   * DOM helpers
   * ----------------------------- */
  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function getCsrfToken() {
    const v = qs("#commentEditCsrfToken")?.value;
    if (v && v !== "NOTPROVIDED") return v;
    return qs("input[name='csrfmiddlewaretoken']")?.value || "";
  }

  // textarea innerHTML로 주입되므로 최소 escape(HTML로 깨지지 않도록)
  function escapeForTextarea(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  /* -----------------------------
   * UI helpers
   * ----------------------------- */
  function restoreStaticText(container, text) {
    // 기존 편집폼 제거
    qs("form.comment-edit-form", container)?.remove();

    // 본문 복구(p.comment-text)
    const p = document.createElement("p");
    p.className = "mb-0 small comment-text";
    p.style.whiteSpace = "pre-wrap";
    p.textContent = text ?? "";
    container.insertBefore(p, container.firstChild);

    // 버튼 그룹 복구
    const actionBtns = qs(".edit-delete-btns", container);
    if (actionBtns) actionBtns.style.display = "";
  }

  function enterEditMode(container, commentId, oldText) {
    const csrf = getCsrfToken();
    if (!csrf) {
      alert("CSRF 토큰을 찾지 못했습니다. 새로고침 후 다시 시도해주세요.");
      container.dataset.editing = "0";
      restoreStaticText(container, oldText);
      return;
    }

    // 버튼 숨김
    const actionBtns = qs(".edit-delete-btns", container);
    if (actionBtns) actionBtns.style.display = "none";

    // 기존 본문 제거
    const textP = qs("p.comment-text", container) || qs("p", container);
    textP?.remove();

    // 편집폼 생성 (기존 서버 POST 로직 재사용)
    const form = document.createElement("form");
    form.method = "post";
    form.className = "comment-edit-form comment-edit-form-js";

    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
      <input type="hidden" name="action_type" value="edit_comment">
      <input type="hidden" name="comment_id" value="${commentId}">
      <textarea name="content"
                class="form-control form-control-sm comment-edit-textarea"
                rows="7">${escapeForTextarea(oldText)}</textarea>
      <div class="comment-edit-actions mt-2 d-flex gap-2">
        <button type="submit" class="btn btn-sm btn-primary px-2 py-1" style="font-size:12px;">저장</button>
        <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-1 cancel-edit" style="font-size:12px;">취소</button>
      </div>
    `;

    container.insertBefore(form, container.firstChild);

    // 취소 버튼
    qs(".cancel-edit", form)?.addEventListener("click", () => {
      container.dataset.editing = "0";
      restoreStaticText(container, oldText);
    });
  }

  /* -----------------------------
   * Event binding (delegation)
   * ----------------------------- */
  function bind() {
    // 중복 바인딩 방지
    if (document.body.dataset[INIT_FLAG] === "1") return;
    document.body.dataset[INIT_FLAG] = "1";

    document.addEventListener("click", (e) => {
      const btn = e.target?.closest?.(".edit-comment-btn");
      if (!btn) return;

      const commentId = btn.dataset.id;
      const container = btn.closest(".comment-content");
      if (!commentId || !container) return;

      if (container.dataset.editing === "1") return;
      container.dataset.editing = "1";

      // 원문 텍스트 확보
      const textP = qs("p.comment-text", container) || qs("p", container);
      const oldText = (textP?.innerText || "").trim();

      enterEditMode(container, commentId, oldText);
    });
  }

  /* -----------------------------
   * Public init
   * ----------------------------- */
  NS.Common.initCommentEdit = function initCommentEdit() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bind, { once: true });
    } else {
      bind();
    }
  };
})();
