// django_ma/static/js/partner/manage_rate/dom_refs.js
export const els = {
  get root() {
    return document.getElementById("manage-rate");
  },

  get yearSelect() {
    return document.getElementById("yearSelect");
  },
  get monthSelect() {
    return document.getElementById("monthSelect");
  },
  get partSelect() {
    return document.getElementById("partSelect");
  },
  get branchSelect() {
    return document.getElementById("branchSelect");
  },
  get btnSearch() {
    return document.getElementById("btnSearchPeriod");
  },

  get inputTable() {
    return document.getElementById("inputTable");
  },
  get mainTable() {
    return document.getElementById("mainTable");
  },
  get btnAddRow() {
    return document.getElementById("btnAddRow");
  },
  get btnResetRows() {
    return document.getElementById("btnResetRows");
  },
  get btnSaveRows() {
    return document.getElementById("btnSaveRows");
  },

  get loadingOverlay() {
    return document.getElementById("loadingOverlay");
  },
};
