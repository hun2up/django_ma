// static/js/partner/manage_structure/index.js
import { fetchData } from "./fetch.js";

/**
 * 📘 Manage Structure (편제변경 페이지)
 * - 연도·월도 드롭다운 생성
 * - superuser의 부서/지점 목록 로드
 * - 검색 버튼 및 자동조회 처리
 */
document.addEventListener("DOMContentLoaded", () => {
  const els = {
    year: document.getElementById("yearSelect"),
    month: document.getElementById("monthSelect"),
    branch: document.getElementById("branchSelect"),
    btnSearch: document.getElementById("btnSearchPeriod"),
    root: document.getElementById("manage-structure"),
  };

  // ✅ 안전 체크
  if (!els.year || !els.month || !els.root) {
    console.error("⚠️ 필수 요소 누락 (year/month/root)");
    return;
  }

  const boot = window.ManageStructureBoot || {};
  const now = new Date();
  const user = window.currentUser || {};

  const selectedYear = Number(boot.selectedYear || now.getFullYear());
  const selectedMonth = Number(boot.selectedMonth || now.getMonth() + 1);

  /* ============================================================
     1️⃣ 연도/월도 드롭다운 채우기
  ============================================================ */
  const fillDropdown = (selectEl, start, end, selectedValue, suffix) => {
    selectEl.innerHTML = "";
    for (let v = start; v <= end; v++) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = `${v}${suffix}`;
      if (v === selectedValue) opt.selected = true;
      selectEl.appendChild(opt);
    }
  };

  fillDropdown(els.year, 2023, 2026, selectedYear, "년");
  fillDropdown(els.month, 1, 12, selectedMonth, "월");

  console.log("✅ 초기화 완료", {
    selectedYear,
    selectedMonth,
    userGrade: user.grade,
    autoLoad: boot.autoLoad,
  });

  /* ============================================================
     2️⃣ Superuser의 부서/지점 목록 로드
  ============================================================ */
  if (user.grade === "superuser") {
    const loadPartsSafely = async (retryCount = 0) => {
      if (typeof window.loadPartsAndBranches !== "function") {
        if (retryCount < 5) {
          console.warn(`⏳ loadPartsAndBranches 대기중 (${retryCount + 1}/5)`);
          return setTimeout(() => loadPartsSafely(retryCount + 1), 300);
        }
        console.error("🚨 loadPartsAndBranches 함수가 정의되지 않았습니다.");
        return;
      }

      try {
        console.log("➡️ 부서/지점 목록 로드 시도");
        await window.loadPartsAndBranches("manage-structure");
        console.log("✅ 부서 목록 로드 완료");
      } catch (err) {
        console.error("❌ 부서 목록 로드 실패:", err);
      }
    };

    // 0.5초 지연 후 시도 (DOM 안정화 보장)
    setTimeout(() => loadPartsSafely(0), 500);
  }

  /* ============================================================
     3️⃣ 검색 버튼 이벤트
  ============================================================ */
  els.btnSearch?.addEventListener("click", () => {
    const year = els.year.value;
    const month = els.month.value;
    const ym = `${year}-${String(month).padStart(2, "0")}`;
    const branch =
      els.branch?.value?.trim() ||
      user.branch?.trim() ||
      "";

    console.log("🔍 검색 버튼 클릭 → fetchData 호출", { ym, branch });
    fetchData(ym, branch);
  });

  /* ============================================================
     4️⃣ main_admin / sub_admin 자동조회
  ============================================================ */
  if (boot.autoLoad) {
    console.log("🟢 autoLoad 활성화됨 (main_admin/sub_admin)");
    const year = els.year.value;
    const month = els.month.value;
    const ym = `${year}-${String(month).padStart(2, "0")}`;
    const branch = user.branch?.trim() || "";

    // 약간의 딜레이 후 fetchData 실행 (초기 렌더 안정화)
    setTimeout(() => {
      console.log("🔄 autoLoad → fetchData 실행", { ym, branch });
      fetchData(ym, branch);
    }, 800);
  }
});
