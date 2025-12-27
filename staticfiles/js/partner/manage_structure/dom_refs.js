// django_ma/static/js/partner/manage_structure/dom_refs.js

export const els = {
  root: document.getElementById("manage-structure"),
  year: document.getElementById("yearSelect"),
  month: document.getElementById("monthSelect"),
  branch: document.getElementById("branchSelect"),
  deadline: document.getElementById("deadlineSelect"),
  btnSearch: document.getElementById("btnSearchPeriod"),
  btnDeadline: document.getElementById("btnSetDeadline"),
  inputSection: document.getElementById("inputSection"),
  btnAddRow: document.getElementById("btnAddRow"),
  btnResetRows: document.getElementById("btnResetRows"),
  btnSaveRows: document.getElementById("btnSaveRows"),
  inputTable: document.getElementById("inputTable"),
  mainTable: document.getElementById("mainTable"),
  loading: document.getElementById("loadingOverlay"),
  searchForm: document.getElementById("searchUserForm"),
  searchKeyword: document.getElementById("searchKeyword"),
  searchResults: document.getElementById("searchResults"),
};

/**
 * ✅ 연/월 초기화는 common/manage_boot.js에서만 수행합니다.
 * 이 함수는 더 이상 사용하지 않도록 비활성화합니다.
 */
export function initSelectOptions() {
  // intentionally no-op
}
