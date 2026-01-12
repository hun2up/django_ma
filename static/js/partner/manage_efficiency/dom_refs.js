// django_ma/static/js/partner/manage_efficiency/dom_refs.js
// =========================================================
// ✅ DOM references (Manage Efficiency)
// - confirmGroupId 신규 추가
// - 페이지별 element id 기반으로 안전 참조
// =========================================================

export const els = {
  // root
  root: document.getElementById("manage-efficiency"),

  // top controls
  year: document.getElementById("yearSelect"),
  month: document.getElementById("monthSelect"),
  branch: document.getElementById("branchSelect"), // superuser only
  btnSearch: document.getElementById("btnSearchPeriod"),

  // sections
  inputSection: document.getElementById("inputSection"),
  mainSheet: document.getElementById("mainSheet"),

  // input actions
  btnAddRow: document.getElementById("btnAddRow"),
  btnResetRows: document.getElementById("btnResetRows"),
  btnSaveRows: document.getElementById("btnSaveRows"),
  inputTable: document.getElementById("inputTable"),

  // accordion container
  accordion: document.getElementById("confirmGroupsAccordion"),
  sheetNotice: document.getElementById("sheetNotice"),

  // loading
  loading: document.getElementById("loadingOverlay"),

  // confirm upload (modal)
  btnConfirmUploadDo: document.getElementById("btnConfirmUploadDo"),
  confirmFileInput: document.getElementById("confirmFileInput"),
  confirmFileName: document.getElementById("confirmFileName"),

  // ✅ NEW: group id hidden
  confirmGroupId: document.getElementById("confirmGroupId"),

  // legacy
  confirmAttachmentId: document.getElementById("confirmAttachmentId"),
};
