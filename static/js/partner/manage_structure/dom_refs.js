// django_ma/static/js/partner/manage_structure/dom_refs.js
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
  get partSelect() {
    return byId("partSelect");
  },
  get branchSelect() {
    return byId("branchSelect");
  },
  get btnSearch() {
    return byId("btnSearchPeriod");
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
    return byId("mainTable_wrapper"); // DataTables 생성 후 존재
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
