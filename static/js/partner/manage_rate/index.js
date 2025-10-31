// django_ma/static/js/partner/manage_rate/index.js
import { fetchData } from "./fetch.js";
import { initInputRowEvents } from "./input_rows.js";
import { els, initDOMRefs } from "./dom_refs.js";
import { initManageBoot } from "../../common/manage_boot.js";
const { root, boot, user } = initManageBoot("rate");

/**
 * 📘 요율변경 페이지 메인 진입 스크립트
 */
document.addEventListener("DOMContentLoaded", () => {
  initDOMRefs(); // ✅ DOM 요소 연결
  const boot = window.ManageRateBoot || {};
  const user = window.currentUser || {};
  const now = new Date();

  if (!els.root) {
    console.error("❌ #manage-rate 요소를 찾을 수 없습니다.");
    return;
  }

  console.group("📘 요율변경 초기화");

  /* ============================================================
     1️⃣ 연도/월도 선택 초기화
  ============================================================ */
  initSelectOptions(
    els.year,
    els.month,
    Number(boot.selectedYear || now.getFullYear()),
    Number(boot.selectedMonth || now.getMonth() + 1)
  );

  /* ============================================================
     2️⃣ 이벤트 바인딩
  ============================================================ */
  bindEvents(user);

  /* ============================================================
     3️⃣ 요청자 입력 초기화
  ============================================================ */
  if (els.inputTable) initInputRowEvents();

  /* ============================================================
     4️⃣ 자동조회 (main_admin / sub_admin)
  ============================================================ */
  autoLoadData(user, boot);

  console.groupEnd();
});

/* ============================================================
   ✅ 연도·월도 드롭다운 초기화
============================================================ */
function initSelectOptions(yearSelect, monthSelect, selectedY, selectedM) {
  const thisY = new Date().getFullYear();

  if (yearSelect) {
    yearSelect.innerHTML = "";
    for (let y = thisY - 2; y <= thisY + 1; y++) {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = `${y}년`;
      if (y === selectedY) opt.selected = true;
      yearSelect.appendChild(opt);
    }
  }

  if (monthSelect) {
    monthSelect.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = `${m}월`;
      if (m === selectedM) opt.selected = true;
      monthSelect.appendChild(opt);
    }
  }

  console.log("✅ 연도/월도 초기화 완료", { selectedY, selectedM });
}


/* ============================================================
   🔹 Superuser의 부서/지점 목록 로드
============================================================ */
/*
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
      await window.loadPartsAndBranches("manage-rate");
      console.log("✅ 부서 목록 로드 완료");
    } catch (err) {
      console.error("❌ 부서 목록 로드 실패:", err);
    }
  };

  // 0.5초 지연 후 실행 (DOM 안정화 보장)
  setTimeout(() => loadPartsSafely(0), 500);
}
*/

/* ============================================================
   ✅ 검색 버튼 이벤트 등록
============================================================ */
function bindEvents(user) {
  els.btnSearch?.addEventListener("click", () => {
    const year = els.year?.value;
    const month = els.month?.value;
    const ym = `${year}-${String(month).padStart(2, "0")}`;
    const branch = els.branch?.value?.trim() || user.branch?.trim() || "";

    console.log("🔍 요율변경 검색", { ym, branch });

    // 섹션 표시
    els.inputSection?.removeAttribute("hidden");
    els.mainTable?.removeAttribute("hidden");

    fetchData(ym, branch, user);
  });
}

/* ============================================================
   ✅ 자동조회 로직 (main_admin / sub_admin)
============================================================ */
/*
function autoLoadData(user, boot) {
  const { grade } = user;
  if (!["main_admin", "sub_admin"].includes(grade)) return;

  const now = new Date();
  const year = els.year?.value || now.getFullYear();
  const month = els.month?.value || now.getMonth() + 1;
  const ym = `${year}-${String(month).padStart(2, "0")}`;
  const branch = user.branch?.trim() || "";

  console.log(`🟢 자동조회 실행 (${grade})`, { ym, branch });

  setTimeout(() => {
    els.inputSection?.removeAttribute("hidden");
    els.mainTable?.removeAttribute("hidden");
    fetchData(ym, branch, user);
  }, 600);
}
  */
