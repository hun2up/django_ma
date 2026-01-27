// django_ma/static/js/board/task_detail.js
(function () {
  "use strict";

  const INIT_FLAG = "__boardTaskDetailEntryInited";

  function boot() {
    if (document.body.dataset[INIT_FLAG] === "1") return;
    document.body.dataset[INIT_FLAG] = "1";

    // superuser only 페이지여야 함. boot 없으면 조용히 종료
    if (!document.getElementById("taskDetailBoot")) return;

    if (window.Board?.Common?.initCommentEdit) window.Board.Common.initCommentEdit();

    const statusUI = window.Board?.Common?.initStatusUI
      ? window.Board.Common.initStatusUI({
          preset: "task",
          badgeSelectors: [".status-badge"],
        })
      : null;

    if (window.Board?.Common?.initDetailInlineUpdate) {
      window.Board.Common.initDetailInlineUpdate({
        bootId: "taskDetailBoot",
        onSuccess: () => statusUI?.applyAll?.(),
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
