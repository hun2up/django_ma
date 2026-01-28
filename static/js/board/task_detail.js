// django_ma/static/js/board/task_detail.js
// =========================================================
// Task Detail Entry
// - 댓글 인라인 수정(comment_edit)
// - 상태 UI(status_ui) 적용(preset: task)
// - 디테일 인라인 업데이트(detail_inline_update) 성공 시 상태 UI 재적용
// =========================================================

(function () {
  "use strict";

  if (window.Board?.Common?.initCommentEdit) {
    window.Board.Common.initCommentEdit();
  }

  const status = window.Board?.Common?.initStatusUI?.({ preset: "task" });

  if (window.Board?.Common?.initDetailInlineUpdate) {
    window.Board.Common.initDetailInlineUpdate({
      bootId: "taskDetailBoot",
      onSuccess: () => status?.applyAll?.(),
    });
  }
})();
