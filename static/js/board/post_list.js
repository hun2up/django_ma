// django_ma/static/js/board/post_list.js
(function () {
  "use strict";

  const INIT_FLAG = "__boardPostListEntryInited";

  function boot() {
    if (document.body.dataset[INIT_FLAG] === "1") return;
    document.body.dataset[INIT_FLAG] = "1";

    const statusUI = window.Board?.Common?.initStatusUI
      ? window.Board.Common.initStatusUI({
          preset: "post",
          // 배지가 늘어나면 여기만 추가
          badgeSelectors: [".status-badge"],
        })
      : null;

    if (window.Board?.Common?.initListInlineUpdate) {
      window.Board.Common.initListInlineUpdate({
        bootId: "postListBoot",
        idKey: "post_id",
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
