// django_ma/static/js/partner/manage_efficiency/index.js
// =========================================================
// ✅ Manage Efficiency Entry (Final Refactor)
// - root 1회 초기화 가드
// - ManageBoot(efficiency) 연동(실패해도 동작)
// - 컬럼폭 적용(applyInputColWidths)
// - 입력행/확인서 업로드 핸들러 연결
// - 검색(runSearch): YM/Branch 검증 + inputSection/mainSheet 오픈 + fetchData
// - 자동검색: main_admin/sub_admin 기본 autoLoad
// - superuser: branch change 시 자동 재조회
// =========================================================

import { els } from "./dom_refs.js";
import { initInputRowEvents } from "./input_rows.js";
import { fetchData } from "./fetch.js";
import { initManageBoot } from "../../common/manage_boot.js";
import { initConfirmUploadHandlers } from "./confirm_upload.js";
import { applyInputColWidths } from "./col_widths.js";

/* =========================================================
   Debug
========================================================= */
const DEBUG = false;
const log = (...args) => DEBUG && console.log("[efficiency/index]", ...args);
const warn = (...args) => console.warn("[efficiency/index]", ...args);
const err = (...args) => console.error("[efficiency/index]", ...args);

/* =========================================================
   Small utils
========================================================= */
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
   DOM getters (safe)
========================================================= */
function getRoot() {
  return (
    els.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-calculate") ||
    null
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
  return els.branch || document.getElementById("branchSelect");
}
function getSearchBtn() {
  return (
    els.btnSearch ||
    document.getElementById("btnSearchPeriod") ||
    document.getElementById("btnSearch") ||
    null
  );
}

/* =========================================================
   UI helpers
========================================================= */
function openSections() {
  const inputSection = getInputSection();
  const mainSheet = getMainSheet();
  if (inputSection) inputSection.hidden = false;
  if (mainSheet) mainSheet.hidden = false;
}

function ensureInitedOnce(root) {
  if (!root) return false;
  if (root.dataset.inited === "1") return false;
  root.dataset.inited = "1";
  return true;
}

/* =========================================================
   Core
========================================================= */
onReady(() => {
  const root = getRoot();
  if (!root) {
    err("⚠️ manage-efficiency root 요소를 찾을 수 없습니다.");
    return;
  }
  if (!ensureInitedOnce(root)) return;

  // 1) 컬럼폭(수동) 적용: dataset 기반
  try {
    const inputTable = document.getElementById("inputTable");
    // applyInputColWidths(root, inputTable);
    log("✅ applyInputColWidths OK");
  } catch (e) {
    warn("⚠️ applyInputColWidths 실패(무시):", e);
  }

  // 2) ManageBoot 연동(실패해도 동작)
  let ctx = {};
  try {
    ctx = initManageBoot("efficiency") || {};
  } catch (e) {
    warn("⚠️ initManageBoot('efficiency') 실패(무시):", e);
    ctx = {};
  }

  const boot = ctx.boot || window.ManageefficiencyBoot || {};
  const user = ctx.user || window.currentUser || {};

  /* -------------------------
     Context getters
  ------------------------- */
  const getGrade = () => str(user.grade || root.dataset.userGrade);

  const getYM = () => {
    const y = str(getYearEl()?.value || "");
    const m = pad2(getMonthEl()?.value || "");
    return y && m ? `${y}-${m}` : "";
  };

  const getBranch = () => {
    const grade = getGrade();
    // superuser: branchSelect 값만 인정(템플릿에서 선택)
    if (grade === "superuser") return str(getBranchEl()?.value || "");
    // 그 외: 로그인 사용자/boot/dataset 순으로
    return (
      str(user.branch) ||
      str(boot.branch) ||
      str(root.dataset.branch) ||
      str(root.dataset.userBranch) ||
      ""
    );
  };

  /* -------------------------
     Init modules (safe)
  ------------------------- */
  try {
    initInputRowEvents();
    console.log("✅ [efficiency] initInputRowEvents OK");
  } catch (e) {
    err("❌ [efficiency] initInputRowEvents 오류:", e);
  }

  try {
    initConfirmUploadHandlers();
    console.log("✅ [efficiency] initConfirmUploadHandlers OK");
  } catch (e) {
    err("❌ [efficiency] initConfirmUploadHandlers 오류:", e);
  }

  /* -------------------------
     Search runner
  ------------------------- */
  async function runSearch(trigger = "click") {
    const grade = getGrade();
    const ym = getYM();
    const branch = getBranch();

    if (!ym) {
      alert("연도/월도를 확인해주세요.");
      return;
    }

    // superuser는 branchSelect가 반드시 있어야 함
    if (grade === "superuser") {
      const branchEl = getBranchEl();
      if (!branchEl) {
        alert("지점 선택 UI가 없습니다. (superuser 템플릿 조건 확인)");
        return;
      }
      if (!str(branchEl.value)) {
        alert("지점을 먼저 선택하세요.");
        return;
      }
    }

    if (!branch) {
      warn("⚠️ branch를 찾지 못했습니다.", {
        trigger,
        grade,
        ym,
        user,
        boot,
        dataset: root.dataset,
      });
      return;
    }

    openSections();
    log("runSearch -> fetchData", { trigger, ym, branch, grade });

    await fetchData(ym, branch);
  }

  /* -------------------------
     Bind events
  ------------------------- */
  const btnSearch = getSearchBtn();
  if (btnSearch) {
    btnSearch.addEventListener("click", () => {
      runSearch("click").catch((e) => err("❌ runSearch(click) 실패:", e));
    });
  }

  const grade = getGrade();

  // 자동 조회 정책:
  // - boot.autoLoad가 boolean이면 그 값을 존중
  // - 아니면 main_admin/sub_admin 기본 autoLoad
  const shouldAuto =
    typeof boot.autoLoad === "boolean"
      ? boot.autoLoad
      : ["main_admin", "sub_admin"].includes(grade);

  if (shouldAuto && ["main_admin", "sub_admin"].includes(grade)) {
    runSearch("auto").catch((e) => err("❌ runSearch(auto) 실패:", e));
  }

  // superuser: branch 변경 시 자동 재조회(선택값 있을 때만)
  const branchEl = getBranchEl();
  if (branchEl && grade === "superuser") {
    branchEl.addEventListener("change", () => {
      if (!str(branchEl.value)) return;
      runSearch("branch-change").catch((e) => err("❌ runSearch(branch-change) 실패:", e));
    });
  }
});
