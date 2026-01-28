// django_ma/static/js/board/task_list.js
// =========================================================
// Task List Entry
// - 상태 UI(status_ui) 적용(preset: task)
// - 리스트 인라인 업데이트(inline_update) 성공 시 상태 UI 재적용
// =========================================================

(function () {
  "use strict";

  const status = window.Board?.Common?.initStatusUI?.({ preset: "task" });

  if (window.Board?.Common?.initListInlineUpdate) {
    window.Board.Common.initListInlineUpdate({
      bootId: "taskListBoot",
      idKey: "task_id",
      onSuccess: () => status?.applyAll?.(),
    });
  }
})();
