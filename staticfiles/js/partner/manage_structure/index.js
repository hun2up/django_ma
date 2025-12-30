// django_ma/static/js/partner/manage_structure/index.js

import { initManageBoot } from "../../common/manage_boot.js";
import { pad2 } from "../../common/manage/ym.js";

function getStaticV() {
  const v = String(window.STATIC_VERSION || "").trim();
  return v ? `?v=${encodeURIComponent(v)}` : "";
}

async function loadPageModules() {
  const v = getStaticV();
  const [{ fetchData }, { initInputRowEvents }] = await Promise.all([
    import(`./fetch.js${v}`),
    import(`./input_rows.js${v}`),
  ]);
  return { fetchData, initInputRowEvents };
}

function safeNum(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function buildYM(y, m) {
  return `${y}-${pad2(m)}`;
}

function getBranchForFetch(ctx, boot) {
  // superuser는 branchSelect 값이 있으면 우선
  if (boot?.userGrade === "superuser") {
    const bs = document.getElementById("branchSelect");
    const v = String(bs?.value || "").trim();
    return v || "";
  }
  // 그 외는 currentUser.branch 우선
  const cu = window.currentUser || {};
  return String(cu.branch || "").trim();
}

function showSections() {
  document.getElementById("inputSection")?.removeAttribute("hidden");
  document.getElementById("mainSheet")?.removeAttribute("hidden");
}

function bindSearchButton(fetchData, boot) {
  const btn = document.getElementById("btnSearchPeriod") || document.getElementById("btnSearch");
  if (!btn || btn.__bound) return;
  btn.__bound = true;

  btn.addEventListener("click", async () => {
    const ySel = document.getElementById("yearSelect");
    const mSel = document.getElementById("monthSelect");

    const y = safeNum(ySel?.value, safeNum(boot?.currentYear, new Date().getFullYear()));
    const m = safeNum(mSel?.value, safeNum(boot?.currentMonth, new Date().getMonth() + 1));

    const ym = buildYM(y, m);
    const branch = getBranchForFetch(null, boot);

    if (boot?.userGrade === "superuser" && !branch) {
      alert("지점을 먼저 선택하세요.");
      return;
    }

    showSections();
    await fetchData(ym, branch);
  });
}

async function runAutoLoadOnce(fetchData, boot) {
  if (window.__structureAutoLoaded) return;
  window.__structureAutoLoaded = true;

  // ✅ payload 우선 사용 (manage_boot에서 준비한 값)
  const payload = window.__manageBootAutoPayload?.structure;
  let ym = payload?.ym || "";
  let branch = payload?.branch || "";

  // payload가 없으면 현재 select 값으로 계산
  if (!ym) {
    const ySel = document.getElementById("yearSelect");
    const mSel = document.getElementById("monthSelect");
    const y = safeNum(ySel?.value, safeNum(boot?.selectedYear || boot?.currentYear, new Date().getFullYear()));
    const m = safeNum(mSel?.value, safeNum(boot?.selectedMonth || boot?.currentMonth, new Date().getMonth() + 1));
    ym = buildYM(y, m);
  }

  if (!branch) {
    branch = getBranchForFetch(null, boot);
  }

  // superuser는 지점 선택 전엔 자동조회 보류
  if (boot?.userGrade === "superuser" && !branch) return;
  if (!branch) return;

  showSections();
  await fetchData(ym, branch);
}

/* =========================================================
   Init
========================================================= */
(async function init() {
  const ctx = initManageBoot("structure") || {};
  const boot = ctx.boot || window.ManageStructureBoot || {};

  const { fetchData, initInputRowEvents } = await loadPageModules();

  // 입력행 이벤트
  try {
    initInputRowEvents();
  } catch (e) {
    console.error("❌ initInputRowEvents error:", e);
  }

  // 검색 버튼 바인딩 (항상 최신 fetchData 사용)
  bindSearchButton(fetchData, boot);

  // ✅ 자동조회 (index.js 단독)
  try {
    await runAutoLoadOnce(fetchData, boot);
  } catch (e) {
    console.error("❌ autoLoad fetch error:", e);
  }
})();
