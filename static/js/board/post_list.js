// django_ma/static/js/board/post_list.js
//
// Entry: post_list
(function () {
  "use strict";
  if (!window.Board?.Common?.initListInlineUpdate) return;

  window.Board.Common.initListInlineUpdate({
    bootId: "postListBoot",
    idKey: "post_id",
  });
})();
