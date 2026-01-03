// django_ma/static/js/partner/manage_efficiency/index.js
//
// ✅ Final Refactor (2026-01-03)
// - superuser 포함: 검색 시 inputSection/mainSheet 항상 오픈
// - els 누락/타이밍 문제 대비: DOM fallback(getElementById)
// - runSearch 전 검증 강화 + branch-change 자동조회 유지
// - 중복 초기화 방지 (data-inited)
// - fetchData(ym, branch) 표준 호출 유지
// - ✅ 확인서 업로드 모달 핸들러(initConfirmUploadHandlers) 실제 호출(바인딩) 추가

import { els } from "./dom_refs.js";
import { initInputRowEvents } from "./input_rows.js";
import { fetchData } from "./fetch.js";
import { initManageBoot } from "../../common/manage_boot.js";
import { initConfirmUploadHandlers } from "./confirm_upload.js";

const DEBUG = false;
const log = (...a) => DEBUG && console.log("[efficiency/index]", ...a);

function str(v) {
  return String(v ?? "").trim();
}
function pad2(v) {
  const s = str(v);
  return s ? s.padStart(2, "0") : "";
}
function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn, { once: true });
  } else {
    fn();
  }
}

/* =========================================================
   DOM fallback helpers
========================================================= */
function getRoot() {
  return (
    els.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-rate") ||
    document.getElementById("manage-structure")
  );
}
function getInputSection() {
  return els.inputSection || document.getElementById("inputSection");
}
function getMainSheet() {
  return els.mainSheet || document.getElementById("mainSheet");
}
function getYearEl() {
  return els.year || document.getElementById("yearSelect");
}
function getMonthEl() {
  return els.month || document.getElementById("monthSelect");
}
function getBranchEl() {
  // superuser 템플릿에서만 존재
  return els.branch || document.getElementById("branchSelect");
}
function getSearchBtn() {
  return (
    els.btnSearch ||
    document.getElementById("btnSearchPeriod") ||
    document.getElementById("btnSearch")
  );
}

onReady(() => {
  const root = getRoot();
  if (!root) {
    console.error("⚠️ manage-efficiency root 요소를 찾을 수 없습니다.");
    return;
  }

  // ✅ 중복 초기화 방지
  if (root.dataset.inited === "1") return;
  root.dataset.inited = "1";

  // ✅ Boot 초기화 (실패해도 진행)
  let ctx = {};
  try {
    ctx = initManageBoot("efficiency") || {};
  } catch (e) {
    console.warn("⚠️ initManageBoot('efficiency') 실패(무시):", e);
    ctx = {};
  }

  const boot = ctx.boot || window.ManageefficiencyBoot || {};
  const user = ctx.user || window.currentUser || {};

  function getGrade() {
    return str(user.grade || root.dataset.userGrade);
  }

  function getYM() {
    const y = str(getYearEl()?.value || "");
    const m = pad2(getMonthEl()?.value || "");
    if (!y || !m) return "";
    return `${y}-${m}`;
  }

  function getBranch() {
    const grade = getGrade();

    // ✅ superuser: branchSelect 값이 곧 branch
    if (grade === "superuser") {
      return str(getBranchEl()?.value || "");
    }

    // ✅ main/sub: user > boot > dataset
    return str(user.branch) || str(boot.branch) || str(root.dataset.branch) || "";
  }

  function showSections() {
    const inputSection = getInputSection();
    const mainSheet = getMainSheet();

    // ✅ hidden 속성만 제거하면 됨
    if (inputSection) inputSection.hidden = false;
    if (mainSheet) mainSheet.hidden = false;
  }

  // ✅ 입력행 이벤트 초기화
  if (els.inputTable || document.getElementById("inputTable")) {
    try {
      initInputRowEvents();
      console.log("✅ [efficiency] initInputRowEvents OK");
    } catch (e) {
      console.error("❌ [efficiency] initInputRowEvents 오류:", e);
    }
  }

  // ✅ 확인서 업로드(모달) 이벤트 바인딩
  // - btnConfirmUploadDo.dataset.bound === "1"로 중복 바인딩 방지 로직(confirm_upload.js 내부)
  try {
    initConfirmUploadHandlers();
    console.log("✅ [efficiency] initConfirmUploadHandlers OK");
  } catch (e) {
    console.error("❌ [efficiency] initConfirmUploadHandlers 오류:", e);
  }

  async function runSearch(trigger = "click") {
    const grade = getGrade();
    const ym = getYM();
    const branch = getBranch();

    if (!ym) {
      alert("연도/월도를 확인해주세요.");
      return;
    }

    // ✅ superuser: 지점 필수
    if (grade === "superuser") {
      const branchEl = getBranchEl();
      if (!branchEl) {
        alert("지점 선택 UI가 없습니다. (superuser 템플릿 조건을 확인하세요)");
        return;
      }
      if (!str(branchEl.value)) {
        alert("지점을 먼저 선택하세요.");
        return;
      }
    }

    if (!branch) {
      console.warn("⚠️ branch를 찾지 못했습니다.", {
        trigger,
        grade,
        ym,
        user,
        boot,
        dataset: root.dataset,
      });
      return;
    }

    // ✅ 핵심: superuser 포함 무조건 섹션을 먼저 열어준다
    showSections();

    log("runSearch → fetchData", { trigger, ym, branch, grade });
    await fetchData(ym, branch);
  }

  // ✅ 검색 버튼 (btnSearchPeriod/btnSearch 공용)
  const btnSearch = getSearchBtn();
  if (btnSearch) {
    btnSearch.addEventListener("click", () => {
      runSearch("click").catch((e) => console.error("❌ runSearch 실패:", e));
    });
  }

  // ✅ 자동조회: main/sub는 보장
  const grade = getGrade();
  const shouldAuto =
    typeof boot.autoLoad === "boolean"
      ? boot.autoLoad
      : ["main_admin", "sub_admin"].includes(grade);

  if (shouldAuto && ["main_admin", "sub_admin"].includes(grade)) {
    runSearch("auto").catch((e) => console.error("❌ auto runSearch 실패:", e));
  }

  // ✅ superuser: 지점 변경 시 자동 조회
  const branchEl = getBranchEl();
  if (branchEl && grade === "superuser") {
    branchEl.addEventListener("change", () => {
      if (!str(branchEl.value)) return;
      runSearch("branch-change").catch((e) =>
        console.error("❌ branch-change runSearch 실패:", e)
      );
    });
  }
});
