// django_ma/static/js/board/post_detail.js
//
// Entry: post_detail (comment edit + detail inline update + status color mapping helper)
(function () {
  "use strict";

  // ✅ 공용(댓글 편집 + 인라인 업데이트) 초기화
  if (window.Board?.Common?.initCommentEdit) window.Board.Common.initCommentEdit();
  if (window.Board?.Common?.initDetailInlineUpdate) {
    window.Board.Common.initDetailInlineUpdate({ bootId: "postDetailBoot" });
  }

  // =========================================================
  // ✅ Post 전용 상태 색상 매핑 (Task와 충돌 없음)
  // - 적용 대상:
  //   1) select.status-select (superuser)
  //   2) span.status-badge (non-superuser)
  // - base.css에 정의된 클래스 사용:
  //   status-start / status-progress / status-fix / status-done
  // =========================================================

  const POST_STATUS_CLASS = {
    "확인중": "status-start",
    "진행중": "status-progress",
    "보완요청": "status-fix",
    "완료": "status-done",
    "반려": "status-done", // 반려는 done 계열(회색)로 처리(원하면 별도 클래스 추가 가능)
  };

  function normalizeStatus(v) {
    return String(v ?? "").trim();
  }

  function clearStatusClasses(el) {
    if (!el) return;
    el.classList.remove("status-start", "status-progress", "status-fix", "status-done");
  }

  function applyStatusClass(el, status) {
    if (!el) return;
    const s = normalizeStatus(status);
    const cls = POST_STATUS_CLASS[s];
    clearStatusClasses(el);
    if (cls) el.classList.add(cls);
  }

  function statusFromSelect(sel) {
    // 우선순위: selected option value → data-status
    const opt = sel?.options?.[sel.selectedIndex];
    return normalizeStatus(opt?.value || sel?.dataset?.status || "");
  }

  function statusFromBadge(span) {
    return normalizeStatus(span?.dataset?.status || span?.textContent || "");
  }

  function initPostStatusUI() {
    // 1) superuser select
    const sel = document.querySelector('select.status-select[name="status"]');
    if (sel) {
      applyStatusClass(sel, statusFromSelect(sel));

      sel.addEventListener("change", function () {
        // change 즉시 반영 (AJAX 성공/실패는 detail_inline_update.js가 처리)
        const st = statusFromSelect(sel);
        sel.dataset.status = st; // data-status 동기화
        applyStatusClass(sel, st);
      });
    }

    // 2) non-superuser badge
    const badge = document.querySelector(".status-badge[data-status]");
    if (badge) {
      applyStatusClass(badge, statusFromBadge(badge));
    }
  }

  document.addEventListener("DOMContentLoaded", initPostStatusUI);
})();
