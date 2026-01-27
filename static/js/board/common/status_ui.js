// django_ma/static/js/board/common/status_ui.js
// =========================================================
// Board Common Status UI (FINAL - Preset Edition)
// - post_list / task_list / post_detail / task_detail 공용
// - status-* 클래스는 프로젝트 전역(base.css) 기준으로 고정
// - ✅ preset 지원: "post" | "task" (필요 시 추가 가능)
// - ✅ badge selector 멀티 지원 (배지가 늘어나도 확장 쉬움)
// - select/status badge의 data-status 동기화
//
// 사용법(권장):
//   const statusUI = Board.Common.initStatusUI({ preset: "post" });
//   statusUI.applyAll();
//
// 옵션:
// - preset: "post" | "task"
// - root: document (optional)
// - selectSelector: "select.status-select" (optional)
// - badgeSelectors: [".status-badge", ...] (optional)
// - syncDataset: true|false (optional)
// - map/classes를 직접 넣으면 preset 대신 커스텀 모드로 동작(하위호환)
//
// 권한 전제:
// - 권한은 서버에서 제어. JS는 DOM 없으면 조용히 종료.
// =========================================================

(function () {
  "use strict";

  const Board = (window.Board = window.Board || {});
  Board.Common = Board.Common || {};

  // ---------------------------------------------------------
  // ✅ 전역 클래스 고정(base.css 기준)
  // ---------------------------------------------------------
  const GLOBAL_STATUS_CLASSES = [
    "status-start",
    "status-progress",
    "status-fix",
    "status-done",
    "status-reject",
  ];

  // ---------------------------------------------------------
  // ✅ 프리셋 정의(페이지별 매핑)
  // - post: 확인중/진행중/보완요청/완료/반려
  // - task: 시작전/진행중/보완필요/보완요청/완료
  // ---------------------------------------------------------
  function normalize(v) {
    return String(v ?? "").trim();
  }

  const PRESETS = {
    post: {
      classes: GLOBAL_STATUS_CLASSES,
      map: (status) => {
        switch (normalize(status)) {
          case "확인중":
            return "status-start";
          case "진행중":
            return "status-progress";
          case "보완요청":
            return "status-fix";
          case "완료":
            return "status-done";
          case "반려":
            return "status-reject";
          default:
            return "";
        }
      },
    },
    task: {
      // task는 reject를 안 쓰더라도 전역 제거는 해도 무방(안전)
      classes: GLOBAL_STATUS_CLASSES,
      map: (status) => {
        switch (normalize(status)) {
          case "시작전":
            return "status-start";
          case "진행중":
            return "status-progress";
          case "보완필요":
          case "보완요청":
            return "status-fix";
          case "완료":
            return "status-done";
          default:
            return "";
        }
      },
    },
  };

  const DEFAULTS = {
    root: document,
    selectSelector: "select.status-select",
    // ✅ 배지가 늘어날 수 있으니 배열로 기본 제공
    badgeSelectors: [".status-badge"],
    syncDataset: true,
  };

  function clearClasses(el, classes) {
    if (!el || !Array.isArray(classes)) return;
    classes.forEach((c) => el.classList.remove(c));
  }

  function getStatusFromSelect(sel) {
    const opt = sel?.options?.[sel.selectedIndex];
    return normalize(opt?.value || sel?.dataset?.status || sel?.value || "");
  }

  function getStatusFromBadge(badge) {
    return normalize(badge?.dataset?.status || badge?.textContent || "");
  }

  function applyOne(el, status, opts) {
    if (!el) return;
    clearClasses(el, opts.classes);

    const cls = opts.map ? opts.map(status) : "";
    if (cls) el.classList.add(cls);
  }

  function queryAllBadges(root, badgeSelectors) {
    const sels = Array.isArray(badgeSelectors) ? badgeSelectors : [badgeSelectors];
    const out = [];
    sels.forEach((sel) => {
      if (!sel) return;
      root.querySelectorAll(sel).forEach((el) => out.push(el));
    });
    return out;
  }

  function applyAll(opts) {
    const root = opts.root || document;

    // select
    root.querySelectorAll(opts.selectSelector).forEach((sel) => {
      const st = getStatusFromSelect(sel);
      if (opts.syncDataset) sel.dataset.status = st;
      applyOne(sel, st, opts);
    });

    // badge (멀티 셀렉터)
    const badges = queryAllBadges(root, opts.badgeSelectors);
    badges.forEach((badge) => {
      const st = getStatusFromBadge(badge);
      if (opts.syncDataset) badge.dataset.status = st;
      applyOne(badge, st, opts);
    });
  }

  function bindLiveUpdate(opts) {
    // select 변경 시 즉시 반영
    document.addEventListener("change", (e) => {
      const el = e.target;
      if (!(el instanceof HTMLSelectElement)) return;
      if (!el.matches(opts.selectSelector)) return;

      const st = getStatusFromSelect(el);
      if (opts.syncDataset) el.dataset.status = st;
      applyOne(el, st, opts);
    });
  }

  function resolveOptions(options) {
    const o = Object.assign({}, DEFAULTS, options || {});

    // 1) 커스텀 모드(하위호환): map/classes 직접 주입
    if (typeof o.map === "function" && Array.isArray(o.classes) && o.classes.length) {
      return o;
    }

    // 2) 프리셋 모드
    const presetName = String(o.preset || "").trim();
    const preset = PRESETS[presetName];
    if (!preset) return null;

    o.map = preset.map;
    o.classes = preset.classes;
    return o;
  }

  /**
   * initStatusUI
   * @param {Object} options
   * @param {string} [options.preset] - "post" | "task"
   * @param {string[]} [options.badgeSelectors] - ex) [".status-badge", ".status-pill"]
   * @returns {{applyAll:Function}|null}
   */
  Board.Common.initStatusUI = function initStatusUI(options) {
    const opts = resolveOptions(options);
    if (!opts) return null;

    const boot = () => {
      applyAll(opts);
      bindLiveUpdate(opts);
    };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
      boot();
    }

    return {
      applyAll: () => applyAll(opts),
    };
  };
})();
