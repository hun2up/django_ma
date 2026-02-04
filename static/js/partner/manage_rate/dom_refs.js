// django_ma/static/js/partner/manage_rate/dom_refs.js
// =====================================================
// ✅ DOM References (Safe / Lazy getters)
// - Avoid repeated getElementById calls
// - Gracefully returns null if element does not exist
// - Includes DataTables wrapper helpers
// =====================================================

function byId(id) {
  return document.getElementById(id);
}

function closestResponsive(el) {
  return el?.closest?.(".table-responsive") || null;
}

export const els = {
  /* =========================
     Root + dataset accessor
     ========================= */
  get root() {
    return byId("manage-rate");
  },

  /**
   * Read a dataset value safely (trimmed)
   * @param {string} key camelCase dataset key
   * @param {string} fallback default
   */
  dataset(key, fallback = "") {
    const v = this.root?.dataset?.[key];
    return String(v ?? fallback).trim();
  },

  /* =========================
     Period / Branch Controls
     ========================= */
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
    return byId("btnSearch");
  },
  get btnSearchPeriod() {
    return byId("btnSearchPeriod");
  },

  /* =========================
     Sections
     ========================= */
  get inputSection() {
    return byId("inputSection");
  },
  get mainSheet() {
    return byId("mainSheet");
  },

  /* =========================
     Tables
     ========================= */
  get inputTable() {
    return byId("inputTable");
  },
  get mainTable() {
    return byId("mainTable");
  },
  get mainTableWrapper() {
    return byId("mainTable_wrapper");
  },
  get mainTableResponsive() {
    return closestResponsive(this.mainTable);
  },

  /* =========================
     Input actions
     ========================= */
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

  /* =========================
     Loading overlay
     ========================= */
  get loadingOverlay() {
    return byId("loadingOverlay");
  },
};
