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

  // =====================================================
  // ✅ 기본 설정값 / Fallback
  // =====================================================
  const selectedYear = parseInt(els.root.dataset.selectedYear) || thisYear;
  const selectedMonth = parseInt(els.root.dataset.selectedMonth) || thisMonth;

  const defaultBranch =
    (els.root.dataset.defaultBranch || "").trim() ||
    (els.branchSelect ? els.branchSelect.value : "") ||
    "";

  // =====================================================
  // ✅ 연도 / 월도 드롭다운 채우기
  // =====================================================
  const fillDropdown = (selectEl, start, end, selectedValue, suffix) => {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    for (let v = start; v <= end; v++) {
      const opt = document.createElement("option");
      opt.value = String(v);
      opt.textContent = `${v}${suffix}`;
      selectEl.appendChild(opt);
    }
    // 강제 세팅 (없는 값일 경우 fallback)
    selectEl.value = String(selectedValue);
    if (!selectEl.value)
      selectEl.value = String(selectedValue === thisYear ? thisYear : thisMonth);
  };

  const yearStart = thisYear - 1;
  const yearEnd = thisYear + 1;
  fillDropdown(els.yearSelect, yearStart, yearEnd, selectedYear, "년");
  fillDropdown(els.monthSelect, 1, 12, selectedMonth, "월");

  console.log("✅ 초기화 완료", {
    selectedYear: els.yearSelect.value,
    selectedMonth: els.monthSelect.value,
    thisYear,
    thisMonth,
  });

  // =====================================================
  // ✅ superuser용 part/branch 자동 로드
  // =====================================================
  if (grade === "superuser" && window.loadPartsAndBranches) {
    console.log("🟢 superuser → 부서/지점 목록 자동 로드 시작");
    window.loadPartsAndBranches("manage-rate");
  }

  // =====================================================
  // ✅ 검색 버튼 클릭 시 데이터 조회
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
  // ✅ main_admin / sub_admin 자동조회
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
