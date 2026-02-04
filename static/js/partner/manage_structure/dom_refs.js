// django_ma/static/js/partner/manage_structure/dom_refs.js
// ------------------------------------------------------
// ✅ DOM References (SSOT)
// - getter 기반으로 DOM을 지연 조회 (BFCache/동적 렌더에 안전)
// - id 변경 시 이 파일만 수정하면 전체 영향 최소화
// ------------------------------------------------------

function byId(id) {
  return document.getElementById(id);
}

export const els = {
  /* root */
  get root() {
    return byId("manage-structure");
  },

  /* controls */
  get yearSelect() {
    return byId("yearSelect");
  },
  get monthSelect() {
    return byId("monthSelect");
  },
  get channelSelect() {
    return byId("channelSelect");
  },
  get partSelect() {
    return byId("partSelect");
  },
  get branchSelect() {
    return byId("branchSelect");
  },
  get btnSearch() {
    return byId("btnSearchPeriod") || byId("btnSearch");
  },

  /* compatibility aliases (legacy usage) */
  get year() {
    return this.yearSelect;
  },
  get month() {
    return this.monthSelect;
  },
  get branch() {
    return this.branchSelect;
  },
  get part() {
    return this.partSelect;
  },

  /* sections */
  get inputSection() {
    return byId("inputSection");
  },
  get mainSheet() {
    return byId("mainSheet");
  },

  /* tables */
  get inputTable() {
    return byId("inputTable");
  },
  get mainTable() {
    return byId("mainTable");
  },
  get mainTableWrapper() {
    return byId("mainTable_wrapper"); // DataTables 생성 후 존재 가능
  },

  /* actions */
  get btnAddRow() {
    return byId("btnAddRow");
  },
  get btnResetRows() {
    return byId("btnResetRows");
  },
  get btnSaveRows() {
    return byId("btnSaveRows");
  },

  /* loading */
  get loadingOverlay() {
    return byId("loadingOverlay");
  },
};
