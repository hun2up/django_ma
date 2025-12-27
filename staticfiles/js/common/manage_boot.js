// django_ma/static/js/common/manage_boot.js
import { fetchData as fetchStructure } from "../partner/manage_structure/fetch.js";
import { fetchData as fetchRate } from "../partner/manage_rate/fetch.js";
import { pad2 } from "./manage/ym.js";

/**
 * ✅ 공통 부트 로더 (Manage Structure / Rate 공용)
 * - DOM 요소 초기화
 * - Boot 데이터(window.ManageStructureBoot / window.ManageRateBoot)
 * - superuser 부서/지점 자동 로드
 * - autoLoad 모드 자동 실행 (fetchData 자동 호출 포함)
 *
 * ✅ 근본 해결:
 * - year/month 초기화는 "여기에서만" 수행
 * - boot가 비어도 root.dataset/current date로 100% 초기화
 * - 다른 파일에서 연/월 채우는 로직은 제거 권장
 */
export function initManageBoot(contextName) {
  const isStructure = contextName === "structure";
  const isRate = contextName === "rate";

  const rootId = isStructure ? "manage-structure" : "manage-rate";
  const root = document.getElementById(rootId);
  if (!root) {
    console.warn(`⚠️ ${rootId} 요소를 찾을 수 없습니다.`);
    return null;
  }

  // ✅ boot/user는 있을 수도/없을 수도 있다. 없어도 동작해야 한다.
  const boot = window.ManageStructureBoot || window.ManageRateBoot || {};
  const user = window.currentUser || {};

  console.group(`🔧 [ManageBoot] 초기화 (${contextName})`);
  console.log("ROOT:", root);
  console.log("BOOT DATA:", boot);
  console.log("USER:", user);

  // ---------- helpers ----------
  const onReady = (fn) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  };

  const readNumber = (v, fallback) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  };

  const getNowYM = () => {
    const now = new Date();
    return { y: now.getFullYear(), m: now.getMonth() + 1 };
  };

  /**
   * ✅ 진짜 “정답” YM 결정 로직
   * 우선순위:
   * 1) boot.selectedYear/Month
   * 2) boot.currentYear/Month
   * 3) root.dataset.selectedYear/Month
   * 4) root.dataset.currentYear/Month
   * 5) Date()
   */
  const getDesiredYM = () => {
    const { y: ny, m: nm } = getNowYM();

    const ds = root.dataset || {};

    const y =
      readNumber(boot.selectedYear, NaN) ||
      readNumber(boot.currentYear, NaN) ||
      readNumber(ds.selectedYear, NaN) ||
      readNumber(ds.currentYear, NaN) ||
      ny;

    const m =
      readNumber(boot.selectedMonth, NaN) ||
      readNumber(boot.currentMonth, NaN) ||
      readNumber(ds.selectedMonth, NaN) ||
      readNumber(ds.currentMonth, NaN) ||
      nm;

    return { y, m };
  };

  /**
   * ✅ 연/월 옵션을 "무조건" 세팅한다.
   * - 옵션이 있든 없든, 최종적으로 value는 항상 원하는 값으로 강제 세팅.
   * - 브라우저별로 "value만 바꾸고 선택이 안 잡히는" 케이스 방지 위해 selected도 같이 처리.
   */
  const forceInitYearMonth = () => {
    const yearSel = document.getElementById("yearSelect");
    const monthSel = document.getElementById("monthSelect");
    if (!yearSel || !monthSel) return false;

    const { y: desiredY, m: desiredM } = getDesiredYM();
    const now = new Date();
    const thisY = now.getFullYear();

    // Year options
    yearSel.innerHTML = "";
    for (let y = thisY - 2; y <= thisY + 1; y++) {
      const opt = document.createElement("option");
      opt.value = String(y);
      opt.textContent = `${y}년`;
      if (y === desiredY) opt.selected = true;
      yearSel.appendChild(opt);
    }

    // Month options
    monthSel.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
      const opt = document.createElement("option");
      opt.value = String(m);
      opt.textContent = `${m}월`;
      if (m === desiredM) opt.selected = true;
      monthSel.appendChild(opt);
    }

    // ✅ value 강제 세팅(일부 브라우저에서 selected만으로 부족한 케이스 방지)
    yearSel.value = String(desiredY);
    monthSel.value = String(desiredM);

    // ✅ change 이벤트 한 번 발생 (외부 로직이 select change를 기대할 때)
    yearSel.dispatchEvent(new Event("change", { bubbles: true }));
    monthSel.dispatchEvent(new Event("change", { bubbles: true }));

    console.log("✅ [ManageBoot] year/month 강제 초기화 완료:", {
      desiredY,
      desiredM,
      yearValue: yearSel.value,
      monthValue: monthSel.value,
    });

    return true;
  };

  const computeYMFromSelect = () => {
    const yearSel = document.getElementById("yearSelect");
    const monthSel = document.getElementById("monthSelect");
    const { y, m } = getDesiredYM();

    const yy = (yearSel?.value || y).toString().trim();
    const mm = (monthSel?.value || m).toString().trim();

    return `${yy}-${pad2(mm)}`;
  };

  const showSections = () => {
    const inputSection = document.getElementById("inputSection");
    const mainSheet = document.getElementById("mainSheet");
    const mainTable = document.getElementById("mainTable");
    inputSection?.removeAttribute("hidden");
    mainSheet?.removeAttribute("hidden");
    mainTable?.removeAttribute("hidden");
  };

  /* ============================================================
     🔹 Superuser용 부서/지점 로드 (공통)
  ============================================================ */
  if ((user.grade || root.dataset.userGrade || "").trim() === "superuser") {
    const loadPartsSafely = async (retryCount = 0) => {
      if (typeof window.loadPartsAndBranches !== "function") {
        if (retryCount < 8) {
          console.warn(`⏳ loadPartsAndBranches 대기중 (${retryCount + 1}/8)`);
          return setTimeout(() => loadPartsSafely(retryCount + 1), 250);
        }
        console.error("🚨 loadPartsAndBranches 함수가 정의되지 않았습니다.");
        return;
      }

      try {
        console.log("➡️ 부서/지점 목록 로드 시도");
        await window.loadPartsAndBranches(rootId);
        console.log("✅ 부서 목록 로드 완료");
      } catch (err) {
        console.error("❌ 부서 목록 로드 실패:", err);
      }
    };

    onReady(() => {
      setTimeout(() => loadPartsSafely(0), 300);
    });
  }

  /* ============================================================
     ✅ 연/월 초기화는 여기서만 (근본 해결)
  ============================================================ */
  onReady(() => {
    const ok = forceInitYearMonth();
    if (!ok) console.warn("⚠️ yearSelect/monthSelect을 찾지 못해 초기화 실패");
  });

  /* ============================================================
     🔹 AutoLoad 모드 (main_admin / sub_admin 공용)
  ============================================================ */
  onReady(async () => {
    const grade = ((user.grade || root.dataset.userGrade) ?? "").toString().trim();
    if (!boot.autoLoad || !["main_admin", "sub_admin"].includes(grade)) return;

    // ✅ autoLoad 전에 연/월을 무조건 확정
    forceInitYearMonth();

    const ym = computeYMFromSelect();
    const branch = (user.branch || root.dataset.branch || "").trim();

    console.log(`🟢 autoLoad 실행 (${contextName})`, { ym, branch });

    showSections();

    try {
      if (isStructure) {
        await fetchStructure(ym, branch, user);
      } else if (isRate) {
        await fetchRate(ym, branch, user);
      }
      console.log("✅ autoLoad → fetchData() 실행 완료");
    } catch (err) {
      console.error("❌ autoLoad fetch 실패:", err);
    }
  });

  console.groupEnd();
  return { root, boot, user };
}
