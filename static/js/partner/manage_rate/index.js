// django_ma/static/js/partner/manage_rate/index.js

import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2 } from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
  if (!els.root) {
    console.error("⚠️ els.root 누락");
    return;
  }

  const now = new Date();
  const thisYear = now.getFullYear();
  const thisMonth = now.getMonth() + 1;

  const grade = els.root.dataset.userGrade || "";
  const selectedYear =
    Number(els.root.dataset.selectedYear) || thisYear;
  const selectedMonth =
    Number(els.root.dataset.selectedMonth) || thisMonth;

  const defaultBranch =
    (els.root.dataset.defaultBranch || "").trim() ||
    (els.branchSelect ? els.branchSelect.value : "") ||
    "";

  // =====================================================
  // ✅ 1. 드롭다운 채우기 함수
  // =====================================================
  const fillDropdown = (selectEl, start, end, selectedValue, suffix) => {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    for (let v = start; v <= end; v++) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = `${v}${suffix}`;
      selectEl.appendChild(opt);
    }
    // ✅ 반드시 선택값 강제 지정 (여기서 핵심!)
    selectEl.value = selectedValue;
  };

  // =====================================================
  // ✅ 2. 연/월 드롭다운 생성 (현재 연월 기준)
  // =====================================================
  const yearStart = thisYear - 1;
  const yearEnd = thisYear + 1;

  fillDropdown(els.yearSelect, yearStart, yearEnd, selectedYear, "년");
  fillDropdown(els.monthSelect, 1, 12, selectedMonth, "월");

  // 다시 한 번 강제 보정 (렌더 후 DOM 안정화용)
  els.yearSelect.value = String(selectedYear);
  els.monthSelect.value = String(selectedMonth);

  console.log("✅ 초기화 완료", {
    selectedYear: els.yearSelect.value,
    selectedMonth: els.monthSelect.value,
    thisYear,
    thisMonth,
  });

  // =====================================================
  // ✅ 3. 검색 버튼 (superuser 수동 조회)
  // =====================================================
  els.btnSearch?.addEventListener("click", () => {
    const yearVal = els.yearSelect?.value || thisYear;
    const monthVal = els.monthSelect?.value || thisMonth;
    const ym = `${yearVal}-${pad2(monthVal)}`;
    const branch =
      (els.branchSelect && els.branchSelect.value) || defaultBranch || "";

    console.log("🔍 [rate/index.js] 검색 → fetchData 실행", { ym, branch });

    fetchData({
      ym,
      branch,
      grade,
      level: els.root.dataset.userLevel || "",
      team_a: els.root.dataset.teamA || "",
      team_b: els.root.dataset.teamB || "",
      team_c: els.root.dataset.teamC || "",
    });
  });

  // =====================================================
  // ✅ 4. main_admin / sub_admin 자동조회
  // =====================================================
  if (["main_admin", "sub_admin"].includes(grade)) {
    const yearVal = els.yearSelect?.value || thisYear;
    const monthVal = els.monthSelect?.value || thisMonth;
    const ym = `${yearVal}-${pad2(monthVal)}`;
    const branch = defaultBranch;

    console.log("🟢 autoLoad → 현재월 기준 자동조회", { ym, branch });

    setTimeout(() => {
      fetchData({
        ym,
        branch,
        grade,
        level: els.root.dataset.userLevel || "",
        team_a: els.root.dataset.teamA || "",
        team_b: els.root.dataset.teamB || "",
        team_c: els.root.dataset.teamC || "",
      });
    }, 600);
  }
});
