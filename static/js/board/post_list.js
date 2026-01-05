// django_ma/static/js/board/post_list.js
// Entry: post_list (status colorize + list inline update)
(function () {
  "use strict";

  const STATUS_CLASSES = ["status-start", "status-progress", "status-fix", "status-done", "status-reject"];

  function normalize(s) {
    return String(s || "").trim();
  }

  // ✅ Post 상태값 매핑
  function mapPostStatus(status) {
    switch (normalize(status)) {
      case "확인중":
        return "status-start";     // 노랑
      case "진행중":
        return "status-progress";  // 초록
      case "보완요청":
        return "status-fix";       // 빨강
      case "완료":
        return "status-done";      // 회색
      case "반려":
        return "status-reject";    // 진회색/회색(추가)
      default:
        return "";
    }
  }

  function apply(el) {
    if (!el) return;
    const status = el.value || el.dataset.status || "";
    STATUS_CLASSES.forEach((c) => el.classList.remove(c));

    const cls = mapPostStatus(status);
    if (cls) el.classList.add(cls);
  }

  function applyAll() {
    document.querySelectorAll(".status-select").forEach(apply);
    document.querySelectorAll(".status-badge").forEach(apply);
  }

  document.addEventListener("DOMContentLoaded", applyAll);

  document.addEventListener("change", (e) => {
    const el = e.target;
    if (!el || !el.classList.contains("status-select")) return;
    apply(el);
  });

  // ✅ 인라인 업데이트 성공 후 색상 재적용
  if (window.Board?.Common?.initListInlineUpdate) {
    window.Board.Common.initListInlineUpdate({
      bootId: "postListBoot",
      idKey: "post_id",
      onSuccess: applyAll,
    });
  }
})();
