// django_ma/static/js/partner/manage_efficiency/index.js
//
// ✅ Refactor (2025-12-29)
// - import 경로에 ?v= 금지 (static manifest/캐시 꼬임 방지)
// - manage_boot(ctx) 실패 시에도 단독 동작 보장
// - superuser 지점 필수 검증 강화
// - main/sub 자동조회 보장 (boot.autoLoad가 없어도 grade 기반)
// - initInputRowEvents 안전 실행 (중복/예외 방지)
// - ym/branch 추출 로직 표준화 + 디버그 로그 강화

import { initInputRowEvents } from "./input_rows.js";
import { fetchData } from "./fetch.js";
import { initManageBoot } from "../../common/manage_boot.js";

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn, { once: true });
  } else {
    fn();
  }
}

function str(v) {
  return String(v ?? "").trim();
}

function pad2(v) {
  const s = str(v);
  return s ? s.padStart(2, "0") : "";
}

onReady(() => {
  // 1) Boot 초기화 (실패해도 계속)
  let ctx = {};
  try {
    ctx = initManageBoot("efficiency") || {};
  } catch (e) {
    console.warn("⚠️ initManageBoot('efficiency') 실패(무시하고 진행):", e);
    ctx = {};
  }

  const root =
    ctx.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-rate") ||   // 혹시 템플릿 id가 흔들릴 때 대비
    document.getElementById("manage-structure");

  if (!root) {
    console.error("⚠️ manage-efficiency root 요소를 찾을 수 없습니다.");
    return;
  }

  const boot = ctx.boot || window.ManageefficiencyBoot || {};
  const user = ctx.user || window.currentUser || {};

  // 2) DOM refs
  const els = {
    year: document.getElementById("yearSelect"),
    month: document.getElementById("monthSelect"),
    branch: document.getElementById("branchSelect"), // superuser만 존재할 수 있음
    btnSearch: document.getElementById("btnSearchPeriod") || document.getElementById("btnSearch"),
    inputSection: document.getElementById("inputSection"),
    mainSheet: document.getElementById("mainSheet"),
    inputTable: document.getElementById("inputTable"),
  };

  if (!els.year || !els.month) {
    console.error("⚠️ yearSelect/monthSelect 요소 누락", {
      year: !!els.year,
      month: !!els.month,
    });
    return;
  }

  function getGrade() {
    return str(user.grade || root.dataset?.userGrade);
  }

  function getYM() {
    const y = str(els.year.value);
    const m = pad2(els.month.value);
    if (!y || !m) return "";
    return `${y}-${m}`;
  }

  function getBranch() {
    const grade = getGrade();

    // ✅ superuser: 셀렉트 우선 (미선택이면 빈값)
    if (grade === "superuser") {
      return str(els.branch?.value);
    }

    // ✅ main/sub: user -> boot -> dataset
    const fromUser = str(user.branch);
    const fromBoot = str(boot.branch);
    const fromDS = str(root.dataset?.branch);
    return fromUser || fromBoot || fromDS || "";
  }

  function showSections() {
    els.inputSection?.removeAttribute("hidden");
    els.mainSheet?.removeAttribute("hidden");
  }

  // 3) 입력행 초기화 (실패해도 페이지는 계속 동작)
  if (els.inputTable) {
    try {
      initInputRowEvents();
      console.log("✅ [efficiency] initInputRowEvents OK");
    } catch (e) {
      console.error("❌ [efficiency] initInputRowEvents 오류:", e);
    }
  }

  async function runSearch(trigger) {
    const grade = getGrade();
    const ym = getYM();
    const branch = getBranch();

    // ✅ superuser는 지점 필수
    if (grade === "superuser") {
      if (!els.branch) {
        alert("지점 선택 UI가 없습니다. (superuser 템플릿 조건을 확인하세요)");
        return;
      }
      if (!str(els.branch.value)) {
        alert("지점을 먼저 선택하세요.");
        return;
      }
    }

    if (!ym) {
      alert("연도/월도를 확인해주세요.");
      return;
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

    showSections();

    console.log("🔍 [efficiency] runSearch → fetchData", { trigger, ym, branch, grade });
    await fetchData(ym, branch);
  }

  // 4) 검색 버튼
  els.btnSearch?.addEventListener("click", () => {
    runSearch("click").catch((e) => console.error("❌ runSearch 실패:", e));
  });

  // 5) 자동 조회 보장
  const grade = getGrade();
  const shouldAuto =
    typeof boot.autoLoad === "boolean"
      ? boot.autoLoad
      : ["main_admin", "sub_admin"].includes(grade);

  if (shouldAuto && ["main_admin", "sub_admin"].includes(grade)) {
    runSearch("auto").catch((e) => console.error("❌ auto runSearch 실패:", e));
  }

  // 6) superuser 지점 선택 변경 시: 자동 조회(원하면)
  // - superuser UX 향상: 지점 선택하면 검색 누르지 않아도 바로 조회 가능
  if (els.branch && getGrade() === "superuser") {
    els.branch.addEventListener("change", () => {
      if (!str(els.branch.value)) return;
      runSearch("branch-change").catch((e) => console.error("❌ branch-change runSearch 실패:", e));
    });
  }
});
