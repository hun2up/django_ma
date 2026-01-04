// django_ma/static/js/board/post_detail.js
//
// Entry: post_detail (comment edit + detail inline update)
(function () {
  "use strict";
  if (window.Board?.Common?.initCommentEdit) window.Board.Common.initCommentEdit();
  if (window.Board?.Common?.initDetailInlineUpdate) {
    window.Board.Common.initDetailInlineUpdate({ bootId: "postDetailBoot" });
  }
})();
