// django_ma/static/js/partner/manage_structure/index.js
import { fetchData } from "./fetch.js";
import { initInputRowEvents } from "./input_rows.js";
import { initManageBoot } from "../../common/manage_boot.js";

/**
 * ✅ Firefox 안정화 핵심:
 * - initManageBoot("structure") 반환값을 바로 구조분해하면
 *   파폭에서 undefined일 때 즉시 TypeError로 스크립트가 죽음
 * - 따라서 safe ctx 패턴으로 처리
 */
const ctx = initManageBoot("structure") || {};
const root = ctx.root || document.getElementById("manage-structure");
const boot = ctx.boot || window.ManageStructureBoot || {};
const user = ctx.user || window.currentUser || {};

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn, { once: true });
  } else {
    fn();
  }
}

onReady(() => {
  if (!root) {
    console.error("⚠️ manage-structure root 요소를 찾을 수 없습니다.");
    return;
  }

  const els = {
    year: document.getElementById("yearSelect"),
    month: document.getElementById("monthSelect"),
    branch: document.getElementById("branchSelect"),
    btnSearch: document.getElementById("btnSearchPeriod"),
    inputSection: document.getElementById("inputSection"),
    mainSheet: document.getElementById("mainSheet"),
    inputTable: document.getElementById("inputTable"),
  };

  if (!els.year || !els.month) {
    console.error("⚠️ yearSelect/monthSelect 요소 누락");
    return;
  }

  // ✅ 요청자 자동입력 초기화
  if (els.inputTable) {
    try {
      initInputRowEvents();
      console.log("✅ 요청자 정보 자동입력 초기화 완료");
    } catch (e) {
      console.error("❌ initInputRowEvents 오류:", e);
    }
  }

  // ✅ 검색 버튼
  els.btnSearch?.addEventListener("click", () => {
    const y = els.year.value;
    const m = String(els.month.value).padStart(2, "0");
    const ym = `${y}-${m}`;

    const branch = els.branch?.value?.trim() || user.branch?.trim() || "";

    els.inputSection?.removeAttribute("hidden");
    els.mainSheet?.removeAttribute("hidden");

    console.log("🔍 검색 클릭 → fetchData", { ym, branch });
    fetchData(ym, branch);
  });

  // ✅ autoLoad fetch 자체는 manage_boot.js에서 하므로
  // 여기서는 화면 표시만 보조
  if (boot.autoLoad && ["main_admin", "sub_admin"].includes((user.grade || "").trim())) {
    els.inputSection?.removeAttribute("hidden");
    els.mainSheet?.removeAttribute("hidden");
  }
});
