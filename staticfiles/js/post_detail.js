/**
 * post_detail.js
 * 게시글 상세 페이지 기능 스크립트
 * - 댓글 수정 기능 (인라인 편집)
 */

document.addEventListener("DOMContentLoaded", () => {
  const editButtons = document.querySelectorAll(".edit-comment-btn");

  editButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const commentId = btn.dataset.id;
      const container = btn.closest(".comment-content");
      const textP = container.querySelector("p");
      const oldText = textP.innerText.trim();

      // 수정버튼 숨김
      const actionBtns = container.querySelector(".edit-delete-btns");
      if (actionBtns) actionBtns.style.display = "none";

      // 폼 생성
      textP.outerHTML = `
        <form method="post" class="d-flex align-items-center gap-1 w-100">
          <input type="hidden" name="action_type" value="edit_comment">
          <input type="hidden" name="comment_id" value="${commentId}">
          <textarea name="content" class="form-control form-control-sm flex-grow-1" rows="1">${oldText}</textarea>
          <button type="submit" class="btn btn-sm btn-primary px-2 py-1" style="font-size:12px;">저장</button>
          <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-1 cancel-edit" style="font-size:12px;">취소</button>
        </form>
      `;

      // 취소 시 새로고침
      container.querySelector(".cancel-edit").addEventListener("click", () => window.location.reload());
    });
  });
});
