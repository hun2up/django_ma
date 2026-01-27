// django_ma/static/js/board/post_detail.js
(function () {
  "use strict";

  const INIT_FLAG = "__boardPostDetailEntryInited";

  function boot() {
    if (document.body.dataset[INIT_FLAG] === "1") return;
    document.body.dataset[INIT_FLAG] = "1";

    if (window.Board?.Common?.initCommentEdit) window.Board.Common.initCommentEdit();

    const statusUI = window.Board?.Common?.initStatusUI
      ? window.Board.Common.initStatusUI({
          preset: "post",
          badgeSelectors: [".status-badge"],
        })
      : null;

    if (window.Board?.Common?.initDetailInlineUpdate) {
      window.Board.Common.initDetailInlineUpdate({
        bootId: "postDetailBoot",
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
