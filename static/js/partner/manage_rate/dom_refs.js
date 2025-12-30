// django_ma/static/js/partner/manage_rate/dom_refs.js
// =====================================================
// ✅ DOM refs (안전형 / 확장형)
// - getById 반복 제거
// - 없으면 null 반환 (페이지/권한/렌더 차이에도 안전)
// - DataTables/반응형 보정에 필요한 wrapper/section 포함
// =====================================================

function byId(id) {
  return document.getElementById(id);
}

function closestTableResponsive(el) {
  if (!el) return null;
  // Bootstrap: .table-responsive
  return el.closest?.(".table-responsive") || null;
}

export const els = {
  /* ---------------------------
     root / dataset helpers
  --------------------------- */
  get root() {
    return byId("manage-rate");
  },

  /**
   * dataset 안전 접근
   * @param {string} key dataset key (camelCase)
   * @param {string} fallback
   */
  dataset(key, fallback = "") {
    const root = byId("manage-rate");
    const v = root?.dataset?.[key];
    return String(v ?? fallback).trim();
  },

  /* ---------------------------
     period / branch controls
  --------------------------- */
  get yearSelect() {
    return byId("yearSelect");
  },
  get monthSelect() {
    return byId("monthSelect");
  },
  get partSelect() {
    return byId("partSelect");
  },
  get branchSelect() {
    return byId("branchSelect");
  },
  get btnSearch() {
    return byId("btnSearchPeriod");
  },

  /* ---------------------------
     sections
  --------------------------- */
  get inputSection() {
    return byId("inputSection");
  },
  get mainSheet() {
    return byId("mainSheet");
  },

  /* ---------------------------
     tables
  --------------------------- */
  get inputTable() {
    return byId("inputTable");
  },
  get mainTable() {
    return byId("mainTable");
  },

  // DataTables가 생성하면 생기는 wrapper
  get mainTableWrapper() {
    // DT가 아직 없으면 null
    return byId("mainTable_wrapper");
  },

  // 메인 테이블을 감싸는 .table-responsive (반응형/가로스크롤 제어)
  get mainTableResponsive() {
    return closestTableResponsive(byId("mainTable"));
  },

  /* ---------------------------
     input actions
  --------------------------- */
  get btnAddRow() {
    return byId("btnAddRow");
  },
  get btnResetRows() {
    return byId("btnResetRows");
  },
  get btnSaveRows() {
    return byId("btnSaveRows");
  },
  get btnCheckTable() {
    return byId("btnCheckTable");
  },

  /* ---------------------------
     overlay
  --------------------------- */
  get loadingOverlay() {
    return byId("loadingOverlay");
  },
};
