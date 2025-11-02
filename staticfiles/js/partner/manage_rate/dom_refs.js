// django_ma/static/js/partner/manage_rate/dom_refs.js
export const els = {
  // ✅ 루트
  root:
    document.getElementById("manage-rate") ||
    document.getElementById("manage-structure"),

  // ✅ 상단 컨트롤
  yearSelect: document.getElementById("yearSelect"),
  monthSelect: document.getElementById("monthSelect"),
  partSelect: document.getElementById("partSelect"),
  branchSelect: document.getElementById("branchSelect"),
  btnSearch: document.getElementById("btnSearchPeriod"),

  // ✅ 내용입력 카드
  inputTable: document.getElementById("inputTable"),
  mainTable: document.getElementById("mainTable"),
  btnAddRow: document.getElementById("btnAddRow"),
  btnResetRows: document.getElementById("btnResetRows"),
  btnSaveRows: document.getElementById("btnSaveRows"),

  // ✅ 공용 로딩
  loadingOverlay: document.getElementById("loadingOverlay"),
};
