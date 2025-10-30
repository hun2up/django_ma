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

  const selectedY = parseInt(window.ManageStructureBoot?.selectedYear ?? thisY, 10);
  const selectedM = parseInt(window.ManageStructureBoot?.selectedMonth ?? thisM, 10);

  // ✅ 연도 목록 채우기
  if (els.year) {
    els.year.innerHTML = ""; // 혹시 기존 값 초기화
    for (let y = thisY - 2; y <= thisY + 1; y++) {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = `${y}년`;
      if (y === selectedY) opt.selected = true;
      els.year.appendChild(opt);
    }
  }

  // ✅ 월도 목록 채우기
  if (els.month) {
    els.month.innerHTML = ""; // 혹시 기존 값 초기화
    for (let m = 1; m <= 12; m++) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = `${m}월`;
      if (m === selectedM) opt.selected = true;
      els.month.appendChild(opt);
    }
  }

  // ✅ 확인용 로그 (테스트 끝나면 제거 가능)
  console.log("[initSelectOptions] selected year/month 적용 완료:", selectedY, selectedM);
  console.log("[initSelectOptions] year select value:", els.year.value);
  console.log("[initSelectOptions] month select value:", els.month.value);
}

