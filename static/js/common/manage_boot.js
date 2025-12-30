// django_ma/static/js/common/manage_boot.js
// =========================================================
// ✅ Manage Boot (Refactor - Single Fetch Owner)
// - Context별 root/boot 자동 탐색
// - Firefox select value set 안정화(옵션 보장 → value set)
// - superuser 부서/지점 로더(loadPartsAndBranches) 대기/1회 보장
// - ✅ fetch 실행은 하지 않는다 (index.js가 단독 실행)
// - autoLoad payload(ym/branch)를 window.__manageBootAutoPayload에 저장
// - 중복 초기화 방지
// =========================================================

console.log("✅ manage_boot.js LOADED", {
  build: "2025-12-30-manageboot-single-fetch-owner",
  url: import.meta?.url,
});

import { pad2 } from "./manage/ym.js";

/* =========================================================
   Global guards
========================================================= */
window.__manageBootInited = window.__manageBootInited || {};
window.__manageBootCtx = window.__manageBootCtx || {};
window.__manageBootPartsLoaded = window.__manageBootPartsLoaded || {};
window.__manageBootAutoPayload = window.__manageBootAutoPayload || {};

/* =========================================================
   Ready helper
========================================================= */
function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn, { once: true });
  } else {
    fn();
  }
}

/* =========================================================
   Small utils
========================================================= */
function toStr(v) {
  return String(v ?? "").trim();
}
function readNumber(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}
function nowYM() {
  const d = new Date();
  return { y: d.getFullYear(), m: d.getMonth() + 1 };
}
function getGrade(user, root) {
  return toStr(user?.grade || root?.dataset?.userGrade);
}
function getBranch({ user, boot, root }) {
  return (
    toStr(user?.branch) ||
    toStr(boot?.branch) ||
    toStr(root?.dataset?.branch) ||
    toStr(root?.dataset?.userBranch) ||
    ""
  );
}

/* =========================================================
   Firefox-safe select init
========================================================= */
function ensureYearOptions(el, baseYear) {
  if (!el) return;
  if (el.options && el.options.length > 0) return;

  const y = Number(baseYear) || new Date().getFullYear();
  for (let yy = y - 2; yy <= y + 1; yy++) {
    const opt = document.createElement("option");
    opt.value = String(yy);
    opt.textContent = `${yy}년`;
    el.appendChild(opt);
  }
}
function ensureMonthOptions(el) {
  if (!el) return;
  if (el.options && el.options.length > 0) return;

  for (let mm = 1; mm <= 12; mm++) {
    const opt = document.createElement("option");
    opt.value = String(mm);
    opt.textContent = `${mm}월`;
    el.appendChild(opt);
  }
}
function setSelectValueSafe(el, value) {
  if (!el) return false;
  const v = toStr(value);
  if (!v) return false;

  const has = Array.from(el.options || []).some((o) => o.value === v);
  if (!has) return false;

  el.value = v;
  return true;
}

/* =========================================================
   Desired YM (Boot 우선)
========================================================= */
function getDesiredYM({ root, boot }) {
  const ds = root?.dataset || {};
  const { y: ny, m: nm } = nowYM();

  const y =
    readNumber(boot?.selectedYear, NaN) ||
    readNumber(boot?.currentYear, NaN) ||
    readNumber(ds?.selectedYear, NaN) ||
    readNumber(ds?.currentYear, NaN) ||
    ny;

  const m =
    readNumber(boot?.selectedMonth, NaN) ||
    readNumber(boot?.currentMonth, NaN) ||
    readNumber(ds?.selectedMonth, NaN) ||
    readNumber(ds?.currentMonth, NaN) ||
    nm;

  return { y, m };
}

function initYearMonthSelects({ root, boot }) {
  const yearEl = document.getElementById("yearSelect");
  const monthEl = document.getElementById("monthSelect");
  if (!yearEl || !monthEl) return { ok: false, yearEl, monthEl };

  const { y, m } = getDesiredYM({ root, boot });

  ensureYearOptions(yearEl, y);
  ensureMonthOptions(monthEl);

  const okY = setSelectValueSafe(yearEl, y);
  const okM = setSelectValueSafe(monthEl, m);

  if (okY) yearEl.dispatchEvent(new Event("change", { bubbles: true }));
  if (okM) monthEl.dispatchEvent(new Event("change", { bubbles: true }));

  console.log("✅ [ManageBoot] year/month init:", {
    desiredY: y,
    desiredM: m,
    yearValue: yearEl.value,
    monthValue: monthEl.value,
    okY,
    okM,
  });

  return { ok: okY && okM, yearEl, monthEl };
}

function computeYMFromSelect({ root, boot }) {
  const yearEl = document.getElementById("yearSelect");
  const monthEl = document.getElementById("monthSelect");

  const { y, m } = getDesiredYM({ root, boot });
  const yy = toStr(yearEl?.value || y);
  const mm = pad2(toStr(monthEl?.value || m));
  return `${yy}-${mm}`;
}

/* =========================================================
   Show sections (payload 준비용: 보여주기만)
========================================================= */
function showSections() {
  document.getElementById("inputSection")?.removeAttribute("hidden");
  document.getElementById("mainSheet")?.removeAttribute("hidden");
}

/* =========================================================
   superuser parts/branches loader
========================================================= */
function loadPartsForSuperuserOnce(rootId) {
  if (!rootId) return;
  if (window.__manageBootPartsLoaded[rootId]) return;
  window.__manageBootPartsLoaded[rootId] = true;

  const tryLoad = async (retry = 0) => {
    if (typeof window.loadPartsAndBranches !== "function") {
      if (retry < 12) {
        console.warn(`⏳ loadPartsAndBranches 대기중 (${retry + 1}/12)`);
        return setTimeout(() => tryLoad(retry + 1), 250);
      }
      console.error("🚨 loadPartsAndBranches 함수가 정의되지 않았습니다.");
      return;
    }

    try {
      console.log("➡️ 부서/지점 목록 로드 시도:", rootId);
      await window.loadPartsAndBranches(rootId);
      console.log("✅ 부서/지점 목록 로드 완료:", rootId);
    } catch (e) {
      console.error("❌ 부서/지점 목록 로드 실패:", e);
    }
  };

  setTimeout(() => tryLoad(0), 150);
}

/* =========================================================
   Root/Boot resolver
========================================================= */
function resolveRootId(ctxName) {
  if (ctxName === "structure") return "manage-structure";
  if (ctxName === "rate") return "manage-rate";
  if (ctxName === "efficiency") return "manage-efficiency";
  return null;
}

function resolveBoot(ctxName) {
  if (ctxName === "structure") return window.ManageStructureBoot || {};
  if (ctxName === "rate") return window.ManageRateBoot || {};
  if (ctxName === "efficiency") return window.ManageefficiencyBoot || {};
  return {};
}

/* =========================================================
   ✅ initManageBoot (NO FETCH)
========================================================= */
export function initManageBoot(contextName) {
  const ctxName = toStr(contextName);
  console.log("✅ initManageBoot called:", { contextName, ctxName });

  if (!ctxName) return null;

  // 컨텍스트별 1회만
  if (window.__manageBootInited[ctxName]) {
    return window.__manageBootCtx[ctxName] || {};
  }
  window.__manageBootInited[ctxName] = true;

  const rootId = resolveRootId(ctxName);
  const root = rootId ? document.getElementById(rootId) : null;

  if (!root) {
    console.warn(`⚠️ ManageBoot root 없음: ${rootId || ctxName}`, { ctxName, rootId });
    window.__manageBootCtx[ctxName] = {};
    return null;
  }

  const boot = resolveBoot(ctxName);
  const user = window.currentUser || {};
  const ctxObj = { root, boot, user };

  window.__manageBootCtx[ctxName] = ctxObj;

  console.group(`🔧 [ManageBoot] 초기화 (${ctxName})`);
  console.log("ROOT:", root);
  console.log("BOOT:", boot);
  console.log("USER:", user);

  // superuser: parts/branches 로드
  onReady(() => {
    const grade = getGrade(user, root);
    if (grade === "superuser") loadPartsForSuperuserOnce(rootId);
  });

  // year/month init + autoload payload 준비
  onReady(() => {
    const grade = getGrade(user, root);

    const autoLoad =
      typeof boot.autoLoad === "boolean"
        ? boot.autoLoad
        : ["main_admin", "sub_admin"].includes(grade);

    initYearMonthSelects({ root, boot });

    // ✅ payload는 main_admin/sub_admin만 자동 준비
    if (!autoLoad || !["main_admin", "sub_admin"].includes(grade)) {
      console.log("🟡 autoLoad payload skip:", { ctxName, grade, autoLoad });
      console.groupEnd();
      return;
    }

    const ym = computeYMFromSelect({ root, boot });
    const branch = getBranch({ user, boot, root });

    if (!branch) {
      console.warn("⚠️ autoLoad payload 중단: branch 없음", { ctxName, grade, boot, ds: root.dataset });
      console.groupEnd();
      return;
    }

    // ✅ show는 해도 되지만, fetch는 index.js가 수행
    showSections();

    window.__manageBootAutoPayload[ctxName] = { ym, branch };

    console.log("🟢 autoLoad payload ready:", { ctxName, ym, branch });
    console.groupEnd();
  });

  try {
    console.groupEnd();
  } catch (_) {}

  return ctxObj;
}
