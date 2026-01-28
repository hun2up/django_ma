// django_ma/static/js/board/post_list.js
// =========================================================
// Post List Entry (FINAL)
// - 상태 UI(status_ui) 적용
// - 리스트 인라인 업데이트(inline_update) 성공 시 상태 UI 재적용
// =========================================================

(function () {
  "use strict";

  const statusApi = window.Board?.Common?.initStatusUI?.({ preset: "post" }) || null;

  const init = window.Board?.Common?.initListInlineUpdate;
  if (typeof init !== "function") return;

  init({
    bootId: "postListBoot",
    idKey: "post_id",
    onSuccess: () => {
      try {
        statusApi?.applyAll?.();
      } catch {
        /* ignore */
      }
    },
  });
})();
