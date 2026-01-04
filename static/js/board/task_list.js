// django_ma/static/js/board/task_list.js
//
// Entry: task_list
(function () {
  "use strict";
  if (!window.Board?.Common?.initListInlineUpdate) return;

  window.Board.Common.initListInlineUpdate({
    bootId: "taskListBoot",
    idKey: "task_id",
  });
})();
