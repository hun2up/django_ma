// django_ma/static/js/partner/manage_rate/dom_refs.js

export const els = {};  // 빈 객체로 시작

// ✅ DOM이 완전히 로드된 뒤 요소 연결
export function initDOMRefs() {
  els.root = document.getElementById("manage-rate");
  els.year = document.getElementById("yearSelect");
  els.month = document.getElementById("monthSelect");
  els.branch = document.getElementById("branchSelect");
  els.btnSearch = document.getElementById("btnSearchPeriod");
  els.inputSection = document.getElementById("inputSection");
  els.inputTable = document.getElementById("inputTable");
  els.mainTable = document.getElementById("mainTable");
  els.loading = document.getElementById("loadingOverlay");

  console.log("🔗 DOM refs initialized:", els.root ? "OK" : "FAIL");
}

export function initSelectOptions() {
  const now = new Date();
  const thisY = now.getFullYear();
  const thisM = now.getMonth() + 1;

  const selectedY = parseInt(window.ManageRateBoot?.selectedYear ?? thisY, 10);
  const selectedM = parseInt(window.ManageRateBoot?.selectedMonth ?? thisM, 10);

  if (els.year) {
    els.year.innerHTML = "";
    for (let y = thisY - 2; y <= thisY + 1; y++) {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = `${y}년`;
      if (y === selectedY) opt.selected = true;
      els.year.appendChild(opt);
    }
  }

  if (els.month) {
    els.month.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = `${m}월`;
      if (m === selectedM) opt.selected = true;
      els.month.appendChild(opt);
    }
  }

  console.log("[initSelectOptions] selected year/month 적용 완료:", selectedY, selectedM);
}
