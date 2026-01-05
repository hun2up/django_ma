// django_ma/static/js/board/task_list.js
(function () {
  "use strict";

  const STATUS_CLASSES = ["status-start", "status-progress", "status-fix", "status-done"];

  function normalize(status) {
    return String(status || "").trim();
  }

  function map(status) {
    switch (normalize(status)) {
      case "시작전":
        return "status-start";
      case "진행중":
        return "status-progress";
      case "보완필요":
      case "보완요청":   // ✅ 둘 다 커버
        return "status-fix";
      case "완료":
        return "status-done";
      default:
        return "";
    }
  }

  function apply(el) {
    if (!el) return;

    // select => value, badge => dataset.status
    const status = el.value || el.dataset.status || "";
    STATUS_CLASSES.forEach((c) => el.classList.remove(c));

    const cls = map(status);
    if (cls) el.classList.add(cls);
  }

  function applyAll() {
    document.querySelectorAll(".status-select").forEach(apply);
    document.querySelectorAll(".status-badge").forEach(apply);
  }

  document.addEventListener("DOMContentLoaded", applyAll);

  // select 변경 시 즉시 반영
  document.addEventListener("change", (e) => {
    const el = e.target;
    if (!el || !el.classList.contains("status-select")) return;
    apply(el);
  });

  // 인라인 업데이트 성공 후에도 재적용
  if (window.Board?.Common?.initListInlineUpdate) {
    window.Board.Common.initListInlineUpdate({
      bootId: "taskListBoot",
      idKey: "task_id",
      onSuccess: applyAll,
    });
  }
})();
