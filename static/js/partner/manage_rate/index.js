// django_ma/static/js/partner/manage_rate/index.js
// =========================================================
// ✅ Manage Rate - Index (Final Refactor)
// - dataset/key 안전화
// - requester autofill 안정화
// - superuser parts/branches loader 대기
// - table check modal 안전화 (bootstrap 유무 대응)
// - ✅ autoload 중복 방지 강화 (manage_boot vs index 전역 가드)
// =========================================================

import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2, alertBox } from "./utils.js";
import { initInputRowEvents } from "./input_rows.js";

/* =========================================================
   constants / guards
========================================================= */
const AUTOLOAD_GRADES = new Set(["head", "leader"]);

// 페이지 중복 init 방지 (BFCache/partial reload 대비)
const INIT_FLAG = "__manageRateIndexInited";

/**
 * 전역 1회 autoload 가드:
 * - manage_boot 또는 index 중 “누군가”가 이미 autoload를 수행하면, 다시는 실행하지 않음.
 */
const AUTOLOAD_FLAG = "__manageRateAutoLoaded";

/* =========================================================
   dataset helpers
========================================================= */
function ds(key, fallback = "") {
  return String(els.root?.dataset?.[key] ?? fallback).trim();
}

function getGrade() {
  return ds("userGrade", window.currentUser?.grade || "");
}

function getDefaultBranch() {
  return ds("defaultBranch", window.currentUser?.branch || "");
}

function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") return String(els.branchSelect?.value || "").trim();
  return getDefaultBranch();
}

function getYMFromSelectors() {
  const y = String(els.yearSelect?.value || "").trim();
  const m = String(els.monthSelect?.value || "").trim();
  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}

function buildFetchPayload(ym) {
  return {
    ym,
    branch: getEffectiveBranch(),
    grade: getGrade(),
    level: ds("userLevel"),
    team_a: ds("teamA"),
    team_b: ds("teamB"),
    team_c: ds("teamC"),
  };
}

/* =========================================================
   requester autofill
========================================================= */
function fillRequesterRow(row) {
  const u = window.currentUser || {};
  const set = (name, val) => {
    const el = row?.querySelector?.(`[name="${name}"]`);
    if (el) el.value = val ?? "";
  };

  set("rq_name", u.name || "");
  set("rq_id", u.id || "");
}

function fillRequesterAllRows() {
  document
    .querySelectorAll("#inputTable tbody tr.input-row")
    .forEach((row) => fillRequesterRow(row));
}

/* =========================================================
   period dropdown (Boot 우선, 단독 실행 대비 fallback 유지)
========================================================= */
function fillDropdown(el, start, end, selected, suffix) {
  if (!el) return;
  el.innerHTML = "";

  for (let v = start; v <= end; v++) {
    const opt = document.createElement("option");
    opt.value = String(v);
    opt.textContent = `${v}${suffix}`;
    el.appendChild(opt);
  }

  el.value = String(selected);
}

function getBootPeriod() {
  const boot = window.ManageRateBoot || {};
  const now = new Date();

  const y = Number(boot.selectedYear || boot.currentYear || now.getFullYear());
  const m = Number(boot.selectedMonth || boot.currentMonth || now.getMonth() + 1);

  return { y, m };
}

function initPeriodDropdowns() {
  const now = new Date();
  const baseY = now.getFullYear();
  const { y: selectedY, m: selectedM } = getBootPeriod();

  fillDropdown(els.yearSelect, baseY - 1, baseY + 1, selectedY, "년");
  fillDropdown(els.monthSelect, 1, 12, selectedM, "월");
}

/* =========================================================
   search
========================================================= */
async function runSearch({ ym, branch } = {}) {
  const finalYM = ym || getYMFromSelectors();
  const finalBranch = branch || getEffectiveBranch();

  if (!finalYM) return alertBox("연도·월도를 선택해주세요.");

  const grade = getGrade();
  if (grade === "superuser" && !finalBranch) return alertBox("부서/지점을 선택해주세요.");
  if (!finalBranch) return alertBox("지점 정보가 없습니다.");

  try {
    await fetchData(buildFetchPayload(finalYM));
  } catch (err) {
    console.error("❌ [rate/index] fetchData 실패:", err);
    alertBox("데이터 조회 중 오류가 발생했습니다.");
  }
}

function initSearchButton() {
  if (!els.btnSearch) return;
  if (els.btnSearch.dataset.bound === "1") return;
  els.btnSearch.dataset.bound = "1";

  els.btnSearch.addEventListener("click", () => runSearch());
}

/* =========================================================
   superuser part/branch loader (대기형)
========================================================= */
function initSuperuserPartsBranchesWait() {
  if (getGrade() !== "superuser") return;

  const tryLoad = (retry = 0) => {
    if (typeof window.loadPartsAndBranches !== "function") {
      if (retry < 12) return setTimeout(() => tryLoad(retry + 1), 250);
      return;
    }
    window.loadPartsAndBranches("manage-rate");
  };

  tryLoad(0);
}

/* =========================================================
   table check modal
========================================================= */
function getTableFetchUrl(branch) {
  const base = ds("tableFetchUrl");
  if (!base) return "";

  const url = new URL(base, window.location.origin);
  url.searchParams.set("branch", branch);
  return url.toString();
}

function escapeAttr(v) {
  return String(v ?? "").replaceAll('"', "&quot;");
}

function renderTableCheckHTML(rows) {
  const tbody = rows
    .map((r) => {
      const t = r.table || r.table_name || "-";
      const rate = r.rate ?? "-";
      return `
        <tr>
          <td class="text-truncate" title="${escapeAttr(t)}">${t}</td>
          <td class="text-center">${rate}</td>
        </tr>`;
    })
    .join("");

  return `
    <div class="table-responsive" style="max-height:300px; overflow-y:auto;">
      <table class="table table-sm table-bordered align-middle mb-0"
             style="font-size:.9rem; table-layout:fixed; width:100%; text-align:center;">
        <colgroup>
          <col style="width:70%;">
          <col style="width:30%;">
        </colgroup>
        <thead class="table-light">
          <tr>
            <th class="text-center">테이블명</th>
            <th class="text-center">요율(%)</th>
          </tr>
        </thead>
        <tbody>${tbody}</tbody>
      </table>
    </div>`;
}

function showBootstrapModal(modalEl) {
  // bootstrap이 없을 수도 있는 환경(스크립트 로드 실패 등) 대비
  const bs = window.bootstrap;
  if (!bs?.Modal) return;

  const inst = bs.Modal.getInstance(modalEl) || new bs.Modal(modalEl);
  inst.show();
}

function initTableCheckModal() {
  const btnCheck = document.getElementById("btnCheckTable");
  const modalBody = document.getElementById("tableCheckBody");
  const modalEl = document.getElementById("tableCheckModal");
  if (!btnCheck || !modalBody || !modalEl) return;

  if (btnCheck.dataset.bound === "1") return;
  btnCheck.dataset.bound = "1";

  btnCheck.addEventListener("click", async () => {
    const branch = getEffectiveBranch();
    if (!branch) return alertBox("지점 정보가 없습니다. 부서/지점을 먼저 선택하세요.");

    const url = getTableFetchUrl(branch);
    if (!url) return alertBox("테이블 조회 URL이 없습니다. (data-table-fetch-url 확인)");

    modalBody.innerHTML = `<div class="py-4 text-muted">불러오는 중...</div>`;
    showBootstrapModal(modalEl);

    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
      if (data.status !== "success") throw new Error(data.message || "조회 실패");

      const rows = Array.isArray(data.rows) ? data.rows : [];
      modalBody.innerHTML = rows.length
        ? renderTableCheckHTML(rows)
        : `<div class="py-4 text-muted">등록된 테이블이 없습니다.</div>`;
    } catch (err) {
      console.error("❌ [rate/index] 테이블 확인 실패:", err);
      modalBody.innerHTML = `<div class="py-4 text-danger">테이블 정보를 불러오지 못했습니다.</div>`;
    }
  });
}

/* =========================================================
   autoload (중복 방지 강화)
   - manage_boot가 autoLoad를 수행했으면 index는 절대 재실행 X
   - manage_boot 미실행/실패 케이스에서만 “보조”로 1회 실행
========================================================= */
function markAutoLoaded() {
  window[AUTOLOAD_FLAG] = true;
}
function isAutoLoaded() {
  return window[AUTOLOAD_FLAG] === true;
}

function shouldAutoLoadByBootOrGrade() {
  const boot = window.ManageRateBoot || {};
  const grade = getGrade();

  // boot.autoLoad가 명시되면 최우선
  if (boot.autoLoad === true) return true;
  if (boot.autoLoad === false) return false;

  // autoLoad 미설정이면 head/leader는 자동
  return AUTOLOAD_GRADES.has(grade);
}

function buildFallbackYM() {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
}

function initAutoLoadAssist() {
  // ✅ 전역 autoload 1회만
  if (isAutoLoaded()) return;

  // ✅ manage_boot가 rate init을 했으면, 여기선 절대 실행하지 않음(충돌 방지)
  if (window.__manageBootInited?.rate) return;

  const grade = getGrade();
  if (!(grade === "superuser" || AUTOLOAD_GRADES.has(grade))) return;

  if (!shouldAutoLoadByBootOrGrade()) return;

  const branch = getEffectiveBranch();
  if (!branch) return;

  const ym = getYMFromSelectors() || buildFallbackYM();

  // 여기서부터 “autoload 실행 확정” — 즉시 가드 올림(중복 클릭/경합 방지)
  markAutoLoaded();

  // UI 초기화/로드 순서 고려하여 약간의 지연
  setTimeout(() => runSearch({ ym, branch }), 250);
}

/* =========================================================
   init
========================================================= */
function init() {
  if (!els.root) return;

  // 페이지 단위 중복 init 방지
  if (els.root.dataset[INIT_FLAG] === "1") return;
  els.root.dataset[INIT_FLAG] = "1";

  initPeriodDropdowns();     // 단독 실행 대비
  initInputRowEvents();      // 입력 이벤트
  fillRequesterAllRows();    // 요청자 자동입력

  initSuperuserPartsBranchesWait();
  initSearchButton();
  initTableCheckModal();

  // ✅ autoload는 보조로만(중복 방지 강화)
  initAutoLoadAssist();
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    init();
  } catch (err) {
    console.error("❌ [manage_rate/index.js 초기화 오류]", err);
  }
});

export { fillRequesterRow, fillRequesterAllRows, runSearch };
