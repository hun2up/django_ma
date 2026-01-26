// django_ma/static/js/partner/manage_structure/input_rows.js
// =======================================================
// 📘 manage_structure 입력행 컨트롤(추가/삭제/초기화/저장)
// - 요청자 자동 입력(표시용 rq_display + hidden rq_name/rq_id 지원)
// - 대상자 10명 제한
// - 저장 후 입력 초기화 + 메인시트 즉시 갱신(fetchData)
// =======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { fetchData } from "./fetch.js";

/* =======================================================
  Constants
======================================================= */
const MAX_ROWS = 10;

/* =======================================================
  Public API
======================================================= */
export function initInputRowEvents() {
  if (!els.inputTable) return;

  // ✅ 버튼 바인딩
  els.btnAddRow?.addEventListener("click", onAddRow);
  els.btnResetRows?.addEventListener("click", onResetRows);
  els.btnSaveRows?.addEventListener("click", onSaveRows);

  // ✅ 삭제 버튼(위임)
  document.addEventListener("click", onRemoveRowDelegated);

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

  const tbody = els.inputTable?.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll(".input-row");
  if (rows.length <= 1) {
    alertBox("행이 하나뿐이라 삭제할 수 없습니다.");
    return;
  }

  btn.closest(".input-row")?.remove();
}

/* =======================================================
  Requester Auto Fill (rq_display + hidden fields)
======================================================= */
function fillRequesterInfo(row) {
  const user = window.currentUser || {};

  const rqNameEl = row.querySelector('input[name="rq_name"]');
  const rqIdEl = row.querySelector('input[name="rq_id"]');
  const rqBranchEl = row.querySelector('input[name="rq_branch"]');
  const rqDispEl = row.querySelector('.rq_display');

  const rqName = user.name || "";
  const rqId = user.id || "";
  const rqBranch = user.branch || "";

  if (rqNameEl) rqNameEl.value = rqName;
  if (rqIdEl) rqIdEl.value = rqId;
  if (rqBranchEl) rqBranchEl.value = rqBranch;

  if (rqDispEl) {
    const n = rqName.trim();
    const i = rqId.trim();
    rqDispEl.value = (n && i) ? `${n}(${i})` : (n || i || "");
  }
}

function setRequesterFields(rowEl, rqName, rqId) {
  // hidden(기존 name 기반) 또는 class 기반 모두 대응
  const nameEl = rowEl.querySelector('input[name="rq_name"], .rq_name');
  const idEl = rowEl.querySelector('input[name="rq_id"], .rq_id');
  const dispEl = rowEl.querySelector(".rq_display");

  if (nameEl) nameEl.value = rqName || "";
  if (idEl) idEl.value = rqId || "";

  if (dispEl) {
    const n = (rqName || "").trim();
    const i = (rqId || "").trim();
    dispEl.value = n && i ? `${n}(${i})` : (n || i || "");
  }
}

function setTargetDisplay(rowEl, tgName, tgId) {
  const nameEl = rowEl.querySelector('input[name="tg_name"]');
  const idEl = rowEl.querySelector('input[name="tg_id"]');
  const dispEl = rowEl.querySelector(".tg_display");

  if (nameEl) nameEl.value = tgName || "";
  if (idEl) idEl.value = tgId || "";

  if (dispEl) {
    const n = (tgName || "").trim();
    const i = (tgId || "").trim();
    dispEl.value = (n && i) ? `${n}(${i})` : (n || i || "");
  }
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

  // select가 있다면 초기화(혹시 구조 변경으로 select가 들어올 수 있어 방어)
  row.querySelectorAll("select").forEach((sel) => {
    sel.selectedIndex = 0;
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

  const payload = {
    month: ym,
    rows: validRows,
    part: user.part || "-",
    branch: branch || "-",
  };

  showLoading("저장 중입니다...");

  try {
    const res = await fetch(boot.dataSaveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.csrfToken,
      },
      body: JSON.stringify(payload),
    });

    const data = await safeJson(res);
    hideLoading();

    if (data?.status !== "success") {
      alertBox(data?.message || "저장 중 오류가 발생했습니다.");
      return;
    }

    alertBox(data?.message || "저장 완료!");

    // ✅ 입력 초기화
    resetInputSection();

    // ✅ 메인시트 갱신(권한 메타 전달)
    const meta = {
      grade: user.grade,
      level: user.level,
      team_a: user.team_a,
      team_b: user.team_b,
      team_c: user.team_c,
    };
    await fetchData(ym, branch, meta);
  } catch (err) {
    console.error("❌ 저장 실패:", err);
    hideLoading();
    alertBox("저장 중 오류가 발생했습니다.");
  }
}

function collectValidRows(rows) {
  const out = [];

  rows.forEach((row) => {
    const tgIdEl = row.querySelector('input[name="tg_id"]');
    const tgNameEl = row.querySelector('input[name="tg_name"]');

    const tg_id = tgIdEl?.value?.trim() || "";
    const tg_name = tgNameEl?.value?.trim() || "";

    // ❌ 대상자 누락 시 제외
    if (!tg_id || !tg_name) return;

    out.push({
      target_id: tg_id,
      target_name: tg_name,
      tg_branch: getVal(row, 'input[name="tg_branch"]'),
      tg_rank: getVal(row, 'input[name="tg_rank"]'),
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

  const year = document.getElementById("yearSelect")?.value;
  const month = document.getElementById("monthSelect")?.value;
  const ym = `${year}-${String(month).padStart(2, "0")}`;

  const branch =
    user.grade === "superuser"
      ? (document.getElementById("branchSelect")?.value || "-").trim() || "-"
      : user.branch || "-";

  return { ym, branch };
}

/* =======================================================
  Helpers
======================================================= */
function getVal(root, selector) {
  const el = root.querySelector(selector);
  return el?.value?.trim?.() ?? "";
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
