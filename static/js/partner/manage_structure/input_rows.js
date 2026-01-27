// django_ma/static/js/partner/manage_structure/input_rows.js
// =======================================================
// 📘 manage_structure 입력행 컨트롤(추가/삭제/초기화/저장) - FINAL
// - 요청자 자동 입력(표시용 rq_display + hidden rq_name/rq_id/rq_branch)
// - 대상자 선택(모달) 시 소속(변경전)=affiliation_display 우선 반영 ✅
// - 대상자 10명 제한
// - 저장 후 입력 초기화 + 메인시트 즉시 갱신(fetchData)
// - 중복 바인딩 방지 + 이벤트 위임 안전화
// =======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";

/* =======================================================
  Constants / State
======================================================= */
const MAX_ROWS = 10;
let bound = false;

/* =======================================================
  Public API
======================================================= */
export function initInputRowEvents() {
  if (bound) return;
  bound = true;

  if (!els.inputTable) return;

  // ✅ 버튼 바인딩
  els.btnAddRow?.addEventListener("click", onAddRow);
  els.btnResetRows?.addEventListener("click", onResetRows);
  els.btnSaveRows?.addEventListener("click", onSaveRows);

  // ✅ 삭제 버튼(위임)
  document.addEventListener("click", onRemoveRowDelegated);

  // ✅ 검색(모달) 버튼 클릭 시 "현재 행" 기억(위임)
  document.addEventListener("click", onOpenSearchDelegated);

  // ✅ 검색 모달에서 "사용자 선택" 이벤트 수신(프로젝트 공용 모달 대응)
  // - components/search_user_modal.html 구현이 무엇이든,
  //   아래 3가지 이벤트 중 하나로 user payload를 받으면 처리하도록 설계
  bindSearchUserSelectionEvents();

  // ✅ 최초 1행 요청자 자동 입력
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) fillRequesterInfo(firstRow);
}

export function resetInputSection() {
  if (!els.inputTable) return;

  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

  // 1) 2행 이상 삭제
  tbody.querySelectorAll(".input-row").forEach((row, idx) => {
    if (idx > 0) row.remove();
  });

  // 2) 첫 행 초기화
  const firstRow = tbody.querySelector(".input-row");
  if (!firstRow) return;

  clearRowInputs(firstRow);
  fillRequesterInfo(firstRow);
  clearTargetInfo(firstRow);
}

/* =======================================================
  Row selection target (modal)
======================================================= */
function setActiveRow(row) {
  if (!row) return;
  // ✅ root에 저장해 다른 모듈에서도 필요 시 접근 가능
  if (els.root) els.root.__activeInputRow = row;
  // ✅ dataset도 가볍게 남김(디버깅/호환)
  row.dataset.active = "1";
}
function getActiveRow() {
  return els.root?.__activeInputRow || els.inputTable?.querySelector('.input-row[data-active="1"]') || null;
}
function clearActiveRowMark() {
  els.inputTable?.querySelectorAll('.input-row[data-active="1"]').forEach((r) => delete r.dataset.active);
}

/* =======================================================
  Event Handlers
======================================================= */
function onAddRow() {
  const tbody = els.inputTable?.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll(".input-row");
  if (rows.length >= MAX_ROWS) {
    alertBox(`대상자는 한 번에 ${MAX_ROWS}명까지 입력 가능합니다.`);
    return;
  }

  const newRow = rows[0].cloneNode(true);

  // ✅ 새 행 초기화(요청자는 다시 채움)
  clearRowInputs(newRow);
  fillRequesterInfo(newRow);
  clearTargetInfo(newRow);
  delete newRow.dataset.active;

  tbody.appendChild(newRow);
}

function onResetRows() {
  if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
  resetInputSection();
}

async function onSaveRows() {
  await saveRowsToServer();
}

function onRemoveRowDelegated(e) {
  const btn = e.target?.closest?.(".btnRemoveRow");
  if (!btn) return;

  const row = btn.closest(".input-row");
  if (!row) return;

  const tbody = els.inputTable?.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll(".input-row");
  if (rows.length <= 1) {
    alertBox("행이 하나뿐이라 삭제할 수 없습니다.");
    return;
  }

  // active row 제거 시 active 해제
  if (els.root?.__activeInputRow === row) els.root.__activeInputRow = null;
  row.remove();
}

function onOpenSearchDelegated(e) {
  const btn = e.target?.closest?.(".btnOpenSearch");
  if (!btn) return;

  const row = btn.closest(".input-row");
  if (!row) return;

  clearActiveRowMark();
  setActiveRow(row);
}

/* =======================================================
  Search Modal selection integration (SSOT)
======================================================= */
function bindSearchUserSelectionEvents() {
  // 1) window 이벤트 (가장 흔한 패턴)
  window.addEventListener("userSelected", (evt) => {
    const user = evt?.detail?.user || evt?.detail || null;
    if (!user) return;
    applySelectedUserToActiveRow(user);
  });

  // 2) document 이벤트 (다른 템플릿에서 document에 dispatch하는 경우)
  document.addEventListener("userSelected", (evt) => {
    const user = evt?.detail?.user || evt?.detail || null;
    if (!user) return;
    applySelectedUserToActiveRow(user);
  });

  // 3) 커스텀 이름 (혹시 기존에 쓰던 이벤트명)
  window.addEventListener("searchUserSelected", (evt) => {
    const user = evt?.detail?.user || evt?.detail || null;
    if (!user) return;
    applySelectedUserToActiveRow(user);
  });
}

function applySelectedUserToActiveRow(user) {
  const row = getActiveRow() || els.inputTable?.querySelector(".input-row");
  if (!row) return;

  // 대상자 세팅
  const tgName = toStr(user.name);
  const tgId = toStr(user.id);
  setTargetDisplay(row, tgName, tgId);

  // ✅ 소속(변경전): affiliation_display 우선 → 없으면 branch
  const aff = toStr(user.affiliation_display);
  const branch = toStr(user.branch);

  const tgBranchEl =
    row.querySelector('input[name="tg_branch"]') ||
    row.querySelector(".tg_branch");

  if (tgBranchEl) tgBranchEl.value = aff || branch || "";

  // 직급(변경전): rank가 있으면
  const rank = toStr(user.rank);
  const tgRankEl =
    row.querySelector('input[name="tg_rank"]') ||
    row.querySelector(".tg_rank");

  if (tgRankEl) tgRankEl.value = rank || "";

  // active mark 해제(다음 선택 시 혼선 방지)
  clearActiveRowMark();
  if (els.root) els.root.__activeInputRow = row;
}

/* =======================================================
  Requester Auto Fill (rq_display + hidden fields)
======================================================= */
function fillRequesterInfo(row) {
  const user = window.currentUser || {};

  const rqNameEl = row.querySelector('input[name="rq_name"]');
  const rqIdEl = row.querySelector('input[name="rq_id"]');
  const rqBranchEl = row.querySelector('input[name="rq_branch"]');
  const rqDispEl = row.querySelector(".rq_display");

  const rqName = toStr(user.name);
  const rqId = toStr(user.id);
  const rqBranch = toStr(user.branch);

  if (rqNameEl) rqNameEl.value = rqName;
  if (rqIdEl) rqIdEl.value = rqId;
  if (rqBranchEl) rqBranchEl.value = rqBranch;

  if (rqDispEl) {
    rqDispEl.value = fmtPerson(rqName, rqId);
  }
}

function setTargetDisplay(rowEl, tgName, tgId) {
  const nameEl = rowEl.querySelector('input[name="tg_name"], .tg_name');
  const idEl = rowEl.querySelector('input[name="tg_id"], .tg_id');
  const dispEl = rowEl.querySelector(".tg_display");

  if (nameEl) nameEl.value = tgName || "";
  if (idEl) idEl.value = tgId || "";

  if (dispEl) dispEl.value = fmtPerson(tgName, tgId);
}

/* =======================================================
  Row Utils
======================================================= */
function clearRowInputs(row) {
  // input 전체 초기화(checkbox 제외)
  row.querySelectorAll("input").forEach((el) => {
    if (el.type === "checkbox") {
      el.checked = false;
      return;
    }
    el.value = "";
  });

  // select가 있다면 초기화(방어)
  row.querySelectorAll("select").forEach((sel) => {
    sel.selectedIndex = 0;
  });
}

function clearTargetInfo(row) {
  // 대상자 관련 필드만 확실히 초기화
  const selectors = [
    'input[name="tg_name"]',
    'input[name="tg_id"]',
    ".tg_display",
    'input[name="tg_branch"]',
    'input[name="tg_rank"]',
    'input[name="chg_branch"]',
    'input[name="chg_rank"]',
    'input[name="memo"]',
    'input[name="or_flag"]',
  ];

  selectors.forEach((sel) => {
    const el = row.querySelector(sel);
    if (!el) return;

    if (el.type === "checkbox") el.checked = false;
    else el.value = "";
  });
}

/* =======================================================
  Save → Server
======================================================= */
async function saveRowsToServer() {
  const tbody = els.inputTable?.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll(".input-row");
  const validRows = collectValidRows(rows);

  if (validRows.length === 0) {
    alertBox("대상자 정보가 입력된 행이 없습니다.");
    return;
  }

  const { ym, branch } = resolveYMAndBranch();
  const user = window.currentUser || {};
  const boot = window.ManageStructureBoot || {};

  const saveUrl = toStr(boot.dataSaveUrl);
  if (!saveUrl) {
    alertBox("저장 URL이 설정되지 않았습니다. (ManageStructureBoot.dataSaveUrl 확인)");
    return;
  }

  const payload = {
    month: ym,
    rows: validRows,
    part: toStr(user.part) || "-",
    branch: toStr(branch) || "-",
  };

  showLoading("저장 중입니다...");

  try {
    const res = await fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken ? getCSRFToken() : (window.csrfToken || ""),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload),
    });

    const data = await safeJson(res);

    if (!res.ok || data?.status !== "success") {
      hideLoading();
      alertBox(data?.message || `저장 중 오류가 발생했습니다. (${res.status})`);
      return;
    }

    hideLoading();
    alertBox(data?.message || "저장 완료!");

    // ✅ 입력 초기화
    resetInputSection();

    // ✅ 메인시트 갱신
    await fetchData(ym, branch);
  } catch (err) {
    console.error("❌ 저장 실패:", err);
    hideLoading();
    alertBox("저장 중 오류가 발생했습니다.");
  }
}

function collectValidRows(rows) {
  const out = [];
  const seen = new Set(); // (선택) 중복 대상자 방지

  rows.forEach((row) => {
    const tg_id = getVal(row, 'input[name="tg_id"], .tg_id');
    const tg_name = getVal(row, 'input[name="tg_name"], .tg_name');

    // ❌ 대상자 누락 시 제외
    if (!tg_id || !tg_name) return;

    // (선택) 동일 대상자 중복 입력 방지
    if (seen.has(tg_id)) return;
    seen.add(tg_id);

    out.push({
      target_id: tg_id,
      target_name: tg_name,

      // ✅ "소속(변경전)"은 이제 affiliation_display가 들어간 값이 tg_branch에 저장됨
      tg_branch: getVal(row, 'input[name="tg_branch"], .tg_branch'),
      tg_rank: getVal(row, 'input[name="tg_rank"], .tg_rank'),

      chg_branch: getVal(row, 'input[name="chg_branch"]'),
      chg_rank: getVal(row, 'input[name="chg_rank"]'),

      memo: getVal(row, 'input[name="memo"]'),
      or_flag: !!row.querySelector('input[name="or_flag"]')?.checked,
    });
  });

  return out;
}

function resolveYMAndBranch() {
  const user = window.currentUser || {};
  const boot = window.ManageStructureBoot || {};

  const ySel = els.yearSelect || document.getElementById("yearSelect");
  const mSel = els.monthSelect || document.getElementById("monthSelect");

  const year = toStr(ySel?.value) || toStr(boot.selectedYear) || toStr(boot.currentYear);
  const month = toStr(mSel?.value) || toStr(boot.selectedMonth) || toStr(boot.currentMonth);

  const ym = `${year}-${String(month || "").padStart(2, "0")}`;

  const branch =
    toStr(user.grade) === "superuser"
      ? toStr(els.branchSelect?.value || document.getElementById("branchSelect")?.value || "-") || "-"
      : toStr(user.branch) || "-";

  return { ym, branch };
}

/* =======================================================
  Helpers
======================================================= */
function toStr(v) {
  return String(v ?? "").trim();
}

function fmtPerson(name, id) {
  const n = toStr(name);
  const i = toStr(id);
  if (n && i) return `${n}(${i})`;
  return n || i || "";
}

function getVal(root, selector) {
  const el = root.querySelector(selector);
  return toStr(el?.value);
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
