// django_ma/static/js/board/common/comment_edit.js
//
// Board Common Comment Inline Edit
// - post_detail / task_detail 공용
// - .edit-comment-btn 클릭 시 인라인 textarea 편집폼 생성
// - CSRF: #commentEditCsrfToken 우선, 없으면 페이지 내 csrf input fallback
// - 취소 시 원복(새로고침 없음)
//
// 전제(템플릿):
// - (권장) hidden input: #commentEditCsrfToken value="{{ csrf_token }}"
// - comment item:
//   - .comment-content[data-comment-id] (권장: data-comment-id)
//   - .edit-comment-btn[data-id]
//   - .edit-delete-btns
//   - p.comment-text

(function () {
  "use strict";

  const Board = (window.Board = window.Board || {});
  Board.Common = Board.Common || {};

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function escapeForTextarea(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function getEditCsrfToken() {
    const v = qs("#commentEditCsrfToken")?.value;
    if (v && v !== "NOTPROVIDED") return v;
    return qs("input[name='csrfmiddlewaretoken']")?.value || "";
  }

  function closeEditMode(container, restoredText) {
    const form = qs("form.comment-edit-form", container);
    if (form) form.remove();

    const p = document.createElement("p");
    p.className = "mb-0 small comment-text";
    p.style.whiteSpace = "pre-wrap";
    p.textContent = restoredText ?? "";
    container.insertBefore(p, container.firstChild);

    const actionBtns = qs(".edit-delete-btns", container);
    if (actionBtns) actionBtns.style.display = "";
  }

  function bind() {
    // 이벤트 위임 (include 분리/DOM 구조 변화에도 안전)
    document.addEventListener("click", (e) => {
      const btn = e.target?.closest?.(".edit-comment-btn");
      if (!btn) return;

      const commentId = btn.dataset.id;
      const container = btn.closest(".comment-content");
      if (!container) return;

      if (container.dataset.editing === "1") return;
      container.dataset.editing = "1";

      const textP = qs("p.comment-text", container) || qs("p", container);
      const oldText = (textP?.innerText || "").trim();

      const actionBtns = qs(".edit-delete-btns", container);
      if (actionBtns) actionBtns.style.display = "none";

      if (textP) textP.remove();

      const csrf = getEditCsrfToken();
      if (!csrf) {
        alert("CSRF 토큰을 찾지 못했습니다. 페이지를 새로고침 후 다시 시도해주세요.");
        container.dataset.editing = "0";
        if (actionBtns) actionBtns.style.display = "";
        // 원문 복구
        closeEditMode(container, oldText);
        return;
      }

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
        <div class="comment-edit-actions">
          <button type="submit" class="btn btn-sm btn-primary px-2 py-1" style="font-size:12px;">저장</button>
          <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-1 cancel-edit" style="font-size:12px;">취소</button>
        </div>
      `;
      container.insertBefore(form, container.firstChild);

      const cancelBtn = qs(".cancel-edit", form);
      if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
          container.dataset.editing = "0";
          closeEditMode(container, oldText);
        });
      }
    });
  }

  Board.Common.initCommentEdit = function initCommentEdit() {
    // ✅ 언제 로드되든 안전하게 바인딩
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bind, { once: true });
    } else {
      bind();
    }
  };
})();
