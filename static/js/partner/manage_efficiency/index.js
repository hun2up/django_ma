// django_ma/static/js/partner/manage_efficiency/index.js
//
// ✅ 그룹(Accordion) 렌더 기준 엔트리
// - 검색 시 inputSection/mainSheet 오픈
// - fetchData(ym, branch) -> 내부에서 groups + rows 렌더
// - confirm 업로드 핸들러/입력행 이벤트 연결

import { els } from "./dom_refs.js";
import { initInputRowEvents } from "./input_rows.js";
import { fetchData } from "./fetch.js";
import { initManageBoot } from "../../common/manage_boot.js";
import { initConfirmUploadHandlers } from "./confirm_upload.js";
import { applyInputColWidths } from "./col_widths.js";

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

function getRoot() {
  return (
    els.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-calculate") ||
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
  return els.branch || document.getElementById("branchSelect");
}
function getSearchBtn() {
  return els.btnSearch || document.getElementById("btnSearchPeriod") || document.getElementById("btnSearch");
}

onReady(() => {
  const root = getRoot();

  const inputTable = document.getElementById("inputTable");
  applyInputColWidths(root, inputTable);
  
  if (!root) {
    console.error("⚠️ manage-efficiency root 요소를 찾을 수 없습니다.");
    return;
  }
  if (root.dataset.inited === "1") return;
  root.dataset.inited = "1";

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
    return y && m ? `${y}-${m}` : "";
  }
  function getBranch() {
    const grade = getGrade();
    if (grade === "superuser") return str(getBranchEl()?.value || "");
    return str(user.branch) || str(boot.branch) || str(root.dataset.branch) || "";
  }

  function showSections() {
    const inputSection = getInputSection();
    const mainSheet = getMainSheet();
    if (inputSection) inputSection.hidden = false;
    if (mainSheet) mainSheet.hidden = false;
  }

  try {
    initInputRowEvents();
    console.log("✅ [efficiency] initInputRowEvents OK");
  } catch (e) {
    console.error("❌ [efficiency] initInputRowEvents 오류:", e);
  }

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

    if (!ym) return alert("연도/월도를 확인해주세요.");

    if (grade === "superuser") {
      const branchEl = getBranchEl();
      if (!branchEl) return alert("지점 선택 UI가 없습니다. (superuser 템플릿 조건 확인)");
      if (!str(branchEl.value)) return alert("지점을 먼저 선택하세요.");
    }
    if (!branch) {
      console.warn("⚠️ branch를 찾지 못했습니다.", { trigger, grade, ym, user, boot, dataset: root.dataset });
      return;
    }

    showSections();
    log("runSearch -> fetchData", { trigger, ym, branch, grade });

    await fetchData(ym, branch);
  }

  const btnSearch = getSearchBtn();
  if (btnSearch) {
    btnSearch.addEventListener("click", () => runSearch("click").catch((e) => console.error("❌ runSearch 실패:", e)));
  }

  const grade = getGrade();
  const shouldAuto = typeof boot.autoLoad === "boolean" ? boot.autoLoad : ["main_admin", "sub_admin"].includes(grade);

  if (shouldAuto && ["main_admin", "sub_admin"].includes(grade)) {
    runSearch("auto").catch((e) => console.error("❌ auto runSearch 실패:", e));
  }

  const branchEl = getBranchEl();
  if (branchEl && grade === "superuser") {
    branchEl.addEventListener("change", () => {
      if (!str(branchEl.value)) return;
      runSearch("branch-change").catch((e) => console.error("❌ branch-change runSearch 실패:", e));
    });
  }
});
