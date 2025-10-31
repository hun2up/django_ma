// django_ma/static/js/common/manage_boot.js

/**
 * ✅ 공통 부트 로더 (Manage Structure / Rate 등 페이지 공용)
 * ----------------------------------------------------------
 * - DOM 요소 초기화
 * - Boot 데이터(window.ManageStructureBoot / window.ManageRateBoot)
 * - superuser 부서/지점 자동 로드
 * - autoLoad 모드 자동 실행
 * ----------------------------------------------------------
 */

export function initManageBoot(contextName) {
  const isStructure = contextName === "structure";
  const isRate = contextName === "rate";

  // 페이지 루트 DOM 자동 탐색
  const rootId = isStructure ? "manage-structure" : "manage-rate";
  const root = document.getElementById(rootId);
  if (!root) {
    console.warn(`⚠️ ${rootId} 요소를 찾을 수 없습니다.`);
    return null;
  }

  // Boot 데이터 자동 결정
  const boot = window.ManageStructureBoot || window.ManageRateBoot || {};
  const user = window.currentUser || {};

  console.log(`🔧 [ManageBoot] 초기화 (${contextName})`, {
    boot,
    userGrade: user.grade,
  });

  /* ============================================================
     🔹 Superuser용 부서/지점 로드 (공통)
  ============================================================ */
  if (user.grade === "superuser") {
    const loadPartsSafely = async (retryCount = 0) => {
      if (typeof window.loadPartsAndBranches !== "function") {
        if (retryCount < 5) {
          console.warn(`⏳ loadPartsAndBranches 대기중 (${retryCount + 1}/5)`);
          return setTimeout(() => loadPartsSafely(retryCount + 1), 400);
        }
        console.error("🚨 loadPartsAndBranches 함수가 정의되지 않았습니다.");
        return;
      }

      try {
        console.log("➡️ 부서/지점 목록 로드 시도");
        await window.loadPartsAndBranches(isStructure ? "manage-structure" : "manage-rate");
        console.log("✅ 부서 목록 로드 완료");
      } catch (err) {
        console.error("❌ 부서 목록 로드 실패:", err);
      }
    };

    // manage_boot.js (수정)
    window.addEventListener("DOMContentLoaded", () => {
        setTimeout(() => loadPartsSafely(0), 600);
    });
  }

  /* ============================================================
     🔹 AutoLoad 모드 (main_admin / sub_admin 공용)
  ============================================================ */
  if (boot.autoLoad && ["main_admin", "sub_admin"].includes(user.grade)) {
    const year = document.getElementById("yearSelect")?.value;
    const month = document.getElementById("monthSelect")?.value;
    const ym = `${year}-${String(month).padStart(2, "0")}`;
    const branch = user.branch?.trim() || "";
    console.log(`🟢 autoLoad 실행 (${contextName})`, { ym, branch });
  }

  console.log(`✅ [ManageBoot] ${contextName} 초기화 완료`);
  return { root, boot, user };
}
