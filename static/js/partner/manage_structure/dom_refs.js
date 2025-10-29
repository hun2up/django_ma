// static/js/partner/manage_structure/dom_refs.js
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

export function initSelectOptions() {
  const now = new Date();
  const thisY = now.getFullYear();
  const thisM = now.getMonth() + 1;

  if (els.year && !els.year.options.length) {
    for (let y = thisY - 2; y <= thisY + 1; y++) {
      els.year.insertAdjacentHTML(
        "beforeend",
        `<option value="${y}" ${y === thisY ? "selected" : ""}>${y}년</option>`
      );
    }
  }

  if (els.month && !els.month.options.length) {
    for (let m = 1; m <= 12; m++) {
      els.month.insertAdjacentHTML(
        "beforeend",
        `<option value="${m}" ${m === thisM ? "selected" : ""}>${m}월</option>`
      );
    }
  }

  if (els.deadline && !els.deadline.options.length) {
    for (let d = 1; d <= 31; d++) {
      els.deadline.insertAdjacentHTML("beforeend", `<option value="${d}">${d}일</option>`);
    }
  }
}
