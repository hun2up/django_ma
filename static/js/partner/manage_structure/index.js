// django_ma/static/js/partner/manage_structure/index.js
// =========================================================
// ✅ Manage Structure - Index (Final Refactor)
// - cache buster(STATIC_VERSION) 기반 모듈 로딩
// - 검색 버튼 1회 바인딩
// - manage_boot auto payload 우선 사용 + 단일 autoLoad
// - ✅ 저장 후 새로고침 UX를 위한 필터 복원(sessionStorage)
// =========================================================

import { initManageBoot } from "../../common/manage_boot.js";
import { pad2 } from "../../common/manage/ym.js";

const FILTER_KEY = "__manage_structure_filters__";

/* =========================================================
   Cache buster
========================================================= */
function getStaticV() {
  const v = String(window.STATIC_VERSION || "").trim();
  return v ? `?v=${encodeURIComponent(v)}` : "";
}

/* =========================================================
   Dynamic import
========================================================= */
async function loadPageModules() {
  const v = getStaticV();
  const [{ fetchData }, { initInputRowEvents }] = await Promise.all([
    import(`./fetch.js${v}`),
    import(`./input_rows.js${v}`),
  ]);
  return { fetchData, initInputRowEvents };
}

/* =========================================================
   Small utils
========================================================= */
function toStr(v) {
  return String(v ?? "").trim();
}

function safeNum(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function buildYM(y, m) {
  return `${y}-${pad2(m)}`;
}

/* =========================================================
   Filter stash/restore (save success → reload)
========================================================= */
function stashFiltersForReload() {
  try {
    const y = toStr(document.getElementById("yearSelect")?.value);
    const m = toStr(document.getElementById("monthSelect")?.value);

    const channel = toStr(document.getElementById("channelSelect")?.value);
    const part = toStr(document.getElementById("partSelect")?.value);
    const branch = toStr(document.getElementById("branchSelect")?.value);

    sessionStorage.setItem(FILTER_KEY, JSON.stringify({ y, m, channel, part, branch }));
  } catch (e) {
    console.warn("⚠️ stashFiltersForReload failed:", e);
  }
}

function restoreFiltersAfterReload() {
  try {
    const raw = sessionStorage.getItem(FILTER_KEY);
    if (!raw) return null;

    sessionStorage.removeItem(FILTER_KEY);

    const data = JSON.parse(raw || "{}");

    // 연/월
    const ySel = document.getElementById("yearSelect");
    const mSel = document.getElementById("monthSelect");
    if (ySel && data.y) ySel.value = data.y;
    if (mSel && data.m) mSel.value = data.m;

    // superuser 셀렉트(없으면 스킵)
    const channelSel = document.getElementById("channelSelect");
    const partSel = document.getElementById("partSelect");
    const branchSel = document.getElementById("branchSelect");

    if (channelSel && data.channel) channelSel.value = data.channel;
    if (partSel && data.part) partSel.value = data.part;
    if (branchSel && data.branch) branchSel.value = data.branch;

    return data;
  } catch (e) {
    console.warn("⚠️ restoreFiltersAfterReload failed:", e);
    return null;
  }
}

/* =========================================================
   Determine branch for fetch
========================================================= */
function getBranchForFetch(boot) {
  // superuser는 branchSelect 값이 있으면 우선
  if (boot?.userGrade === "superuser") {
    const bs = document.getElementById("branchSelect");
    const v = toStr(bs?.value);
    return v || "";
  }

  // 그 외는 currentUser.branch 우선
  const cu = window.currentUser || {};
  return toStr(cu.branch || "");
}

/* =========================================================
   UI
========================================================= */
function showSections() {
  document.getElementById("inputSection")?.removeAttribute("hidden");
  document.getElementById("mainSheet")?.removeAttribute("hidden");
}

/* =========================================================
   Bind search button
========================================================= */
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
    const branch = getBranchForFetch(boot);

    if (boot?.userGrade === "superuser" && !branch) {
      alert("지점을 먼저 선택하세요.");
      return;
    }

    showSections();
    await fetchData(ym, branch);
  });
}

/* =========================================================
   AutoLoad (single-run)
========================================================= */
async function runAutoLoadOnce(fetchData, boot) {
  if (window.__structureAutoLoaded) return;
  window.__structureAutoLoaded = true;

  // ✅ 1) 새로고침 복원값이 있으면 그 값으로 우선 자동조회
  // (save.js에서 stash → reload 한 경우)
  const restored = restoreFiltersAfterReload();
  if (restored) {
    const y = safeNum(restored.y, safeNum(boot?.selectedYear || boot?.currentYear, new Date().getFullYear()));
    const m = safeNum(restored.m, safeNum(boot?.selectedMonth || boot?.currentMonth, new Date().getMonth() + 1));
    const ym = buildYM(y, m);

    const branch =
      boot?.userGrade === "superuser"
        ? toStr(restored.branch) || getBranchForFetch(boot)
        : getBranchForFetch(boot);

    if (boot?.userGrade === "superuser" && !branch) return;
    if (!branch) return;

    showSections();
    await fetchData(ym, branch);
    return;
  }

  // ✅ 2) payload 우선 사용 (manage_boot에서 준비한 값)
  const payload = window.__manageBootAutoPayload?.structure;
  let ym = toStr(payload?.ym || "");
  let branch = toStr(payload?.branch || "");

  // payload가 없으면 현재 select 값으로 계산
  if (!ym) {
    const ySel = document.getElementById("yearSelect");
    const mSel = document.getElementById("monthSelect");
    const y = safeNum(
      ySel?.value,
      safeNum(boot?.selectedYear || boot?.currentYear, new Date().getFullYear())
    );
    const m = safeNum(
      mSel?.value,
      safeNum(boot?.selectedMonth || boot?.currentMonth, new Date().getMonth() + 1)
    );
    ym = buildYM(y, m);
  }

  if (!branch) {
    branch = getBranchForFetch(boot);
  }

  // superuser는 지점 선택 전엔 자동조회 보류
  if (boot?.userGrade === "superuser" && !branch) return;
  if (!branch) return;

  showSections();
  await fetchData(ym, branch);
}

/* =========================================================
   Expose helpers for save.js
========================================================= */
function exposeReloadHelpers() {
  // save.js에서 import 없이도 쓸 수 있게 안전 노출
  window.__manageStructure = window.__manageStructure || {};
  window.__manageStructure.stashFiltersForReload = stashFiltersForReload;
}

/* =========================================================
   Init
========================================================= */
(async function init() {
  const ctx = initManageBoot("structure") || {};
  const boot = ctx.boot || window.ManageStructureBoot || {};

  exposeReloadHelpers();

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
