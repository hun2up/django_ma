// django_ma/static/js/board/post_detail.js
// =========================================================
// Post Detail Entry
// - 댓글 인라인 수정(comment_edit)
// - 상태 UI(status_ui) 적용
// - 디테일 인라인 업데이트(detail_inline_update) 성공 시 상태 UI 재적용
// =========================================================

(function () {
  "use strict";

  // 1) 댓글 인라인 수정(있을 때만)
  if (window.Board?.Common?.initCommentEdit) {
    window.Board.Common.initCommentEdit();
  }

  // 2) 상태 UI(preset: post)
  const status = window.Board?.Common?.initStatusUI?.({ preset: "post" });

  // 3) 담당자/상태 인라인 업데이트(있을 때만)
  if (window.Board?.Common?.initDetailInlineUpdate) {
    window.Board.Common.initDetailInlineUpdate({
      bootId: "postDetailBoot",
      onSuccess: () => status?.applyAll?.(),
    });
  }
})();
