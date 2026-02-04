// django_ma/static/js/partner/manage_rate/input_rows.js
// ======================================================
// 📘 Manage Rate - Input Rows
// - Add / Remove / Reset / Save bindings
// - Modal userSelected event -> fill target + apply dropdowns
// - Superuser branch change: clear cache + reset + apply dropdowns
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { saveRows } from "./save.js";
import { fetchBranchTables, applyTableDropdownToRow, clearTableCache } from "./table_dropdown.js";

/* =========================================================
   Small utils
========================================================= */
function toStr(v) {
  return String(v ?? "").trim();
}

function fmtPerson(name, id) {
  const n = toStr(name);
  const i = toStr(id);
  if (n && i) return `${n}(${i})`;
  return n || i || "";
}

/* =========================================================
   Grade / Branch helpers
========================================================= */
function getGrade() {
  return toStr(els.root?.dataset?.userGrade || window.currentUser?.grade);
}

/**
 * Effective branch resolution (same behavior as before)
 * - superuser: branchSelect > dataset.defaultBranch > currentUser.branch
 * - others: currentUser.branch > dataset.defaultBranch
 */
function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") {
    const v1 = toStr(els.branchSelect?.value);
    const v2 = toStr(els.root?.dataset?.defaultBranch);
    const v3 = toStr(window.currentUser?.branch);
    return v1 || v2 || v3;
  }
  return toStr(window.currentUser?.branch || els.root?.dataset?.defaultBranch);
}

/* =========================================================
   Requester auto-fill (rq_display + hidden fields)
========================================================= */
function fillRequesterInfo(row) {
  const u = window.currentUser || {};
  const rqName = toStr(u.name);
  const rqId = toStr(u.id);

  const rqNameEl = row.querySelector('[name="rq_name"]');
  const rqIdEl = row.querySelector('[name="rq_id"]');
  const rqDispEl = row.querySelector(".rq_display");

  if (rqNameEl) rqNameEl.value = rqName;
  if (rqIdEl) rqIdEl.value = rqId;
  if (rqDispEl) rqDispEl.value = fmtPerson(rqName, rqId);
}

/* =========================================================
   Row reset (new row / reset)
========================================================= */
function resetRowInputs(row) {
  // inputs reset
  row.querySelectorAll("input").forEach((el) => {
    if (el.type === "checkbox") {
      el.checked = false;
      return;
    }
    el.value = "";
    el.readOnly = true; // base: readonly, then unlock needed fields below
  });

  // selects reset
  row.querySelectorAll("select").forEach((sel) => {
    sel.value = "";
  });

  // requester auto-fill
  fillRequesterInfo(row);

  // memo: editable
  const memo = row.querySelector('[name="memo"]');
  if (memo) memo.readOnly = false;

  // after tables: editable until dropdown swap happens
  const aftF = row.querySelector('input[name="after_ftable"]');
  const aftL = row.querySelector('input[name="after_ltable"]');
  if (aftF) aftF.readOnly = false;
  if (aftL) aftL.readOnly = false;

  // display fields remain readonly
  const rqDisp = row.querySelector(".rq_display");
  const tgDisp = row.querySelector(".tg_display");
  if (rqDisp) rqDisp.readOnly = true;
  if (tgDisp) tgDisp.readOnly = true;
}

/* =========================================================
   Active row (modal target selection applies to active row)
========================================================= */
function setActiveRow(row) {
  els.inputTable?.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
  row.classList.add("active");
}

/* =========================================================
   Target detail fetch
========================================================= */
async function fetchTargetDetail(targetId) {
  const base = toStr(els.root?.dataset?.targetDetailUrl);
  const url = base ? new URL(base, window.location.origin) : new URL("/partner/ajax/rate-user-detail/", window.location.origin);
  url.searchParams.set("user_id", toStr(targetId));

  const res = await fetch(url.toString(), {
    headers: { "X-Requested-With": "XMLHttpRequest" },
    credentials: "same-origin",
  });

  let data;
  try {
    data = await res.json();
  } catch {
    data = { status: "error", message: "JSON 파싱 실패" };
  }

  return { ok: res.ok, data };
}

/* =========================================================
   Dropdown apply (branch → tables → apply to all rows)
========================================================= */
async function ensureDropdownsOnAllRows() {
  const branch = getEffectiveBranch();
  if (!branch) return; // superuser may not have selected branch yet

  const tables = await fetchBranchTables(branch);
  const rows = els.inputTable?.querySelectorAll("tbody tr.input-row") || [];
  rows.forEach((row) => applyTableDropdownToRow(row, tables));
}

/* =========================================================
   Target fill (tg_display + hidden fields + before table/rate)
========================================================= */
export async function fillTargetInfo(row, targetId) {
  const id = toStr(targetId);
  if (!id) return;

  try {
    const { ok, data } = await fetchTargetDetail(id);
    if (!ok || data?.status !== "success") {
      return alertBox(data?.message || "대상자 정보를 불러오지 못했습니다.");
    }

    const info = data.data || {};

    // requester fill if missing
    const rqNameEl = row.querySelector('[name="rq_name"]');
    const rqIdEl = row.querySelector('[name="rq_id"]');
    if (rqNameEl && !toStr(rqNameEl.value)) rqNameEl.value = toStr(window.currentUser?.name);
    if (rqIdEl && !toStr(rqIdEl.value)) rqIdEl.value = toStr(window.currentUser?.id);

    const rqDispEl = row.querySelector(".rq_display");
    if (rqDispEl) rqDispEl.value = fmtPerson(toStr(rqNameEl?.value), toStr(rqIdEl?.value));

    // safe set
    const set = (name, val) => {
      const el = row.querySelector(`[name="${name}"]`);
      if (el) el.value = val ?? "";
    };

    // target hidden + display
    const tgName = toStr(info.target_name || info.name);
    const tgId = toStr(info.target_id || info.id);
    set("tg_name", tgName);
    set("tg_id", tgId);

    const tgDisp = row.querySelector(".tg_display");
    if (tgDisp) tgDisp.value = fmtPerson(tgName, tgId);

    // before table/rate
    set("before_ftable", info.non_life_table || "");
    set("before_frate", info.non_life_rate || "");
    set("before_ltable", info.life_table || "");
    set("before_lrate", info.life_rate || "");

    // branch guard (superuser must choose branch first)
    const branch = getEffectiveBranch();
    if (!branch) {
      if (getGrade() === "superuser") alertBox("먼저 부서/지점을 선택한 뒤 대상자를 선택해주세요.");
      return;
    }

    // apply dropdowns for current branch
    await ensureDropdownsOnAllRows();
  } catch (err) {
    console.error("❌ [rate/input_rows] fillTargetInfo error:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}

/* =========================================================
   Reset input section (keeps first row only)
========================================================= */
export function resetInputSection() {
  if (!els.inputTable) return;

  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll(".input-row");
  rows.forEach((r, i) => {
    if (i > 0) r.remove();
  });

  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    resetRowInputs(firstRow);
    setActiveRow(firstRow);
  }
}

/* =========================================================
   Init bindings (once)
========================================================= */
let bound = false;

export function initInputRowEvents() {
  if (bound) return;
  bound = true;

  if (!els.inputTable) return;

  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

  // first row init
  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    resetRowInputs(firstRow);
    setActiveRow(firstRow);
  }

  /* -------------------------
     Add row
     ------------------------- */
  els.btnAddRow?.addEventListener("click", async () => {
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length >= 10) return alertBox("대상자는 한 번에 10명까지 입력 가능합니다.");

    const newRow = rows[0].cloneNode(true);
    resetRowInputs(newRow);
    tbody.appendChild(newRow);
    setActiveRow(newRow);

    await ensureDropdownsOnAllRows();
  });

  /* -------------------------
     Reset
     ------------------------- */
  els.btnResetRows?.addEventListener("click", async () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
    await ensureDropdownsOnAllRows();
  });

  /* -------------------------
     Save
     ------------------------- */
  els.btnSaveRows?.addEventListener("click", () => {
    saveRows();
  });

  /* -------------------------
     Table delegation: remove row / set active
     ------------------------- */
  els.inputTable.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".btnRemoveRow");
    if (removeBtn) {
      const rows = tbody.querySelectorAll(".input-row");
      if (rows.length <= 1) return alertBox("행이 하나뿐이라 삭제할 수 없습니다.");
      removeBtn.closest(".input-row")?.remove();
      return;
    }

    const tr = e.target.closest(".input-row");
    if (tr) setActiveRow(tr);
  });

  /* -------------------------
     Modal event: userSelected
     ------------------------- */
  document.addEventListener("userSelected", async (e) => {
    const targetId = e.detail?.id || e.detail?.user_id || e.detail?.pk;
    if (!targetId) return;

    const activeRow = tbody.querySelector(".input-row.active");
    if (!activeRow) return alertBox("대상자를 입력할 행을 먼저 클릭하세요.");

    showLoading("대상자 정보 불러오는 중...");
    try {
      await fillTargetInfo(activeRow, targetId);
    } finally {
      hideLoading();
    }
  });

  /* -------------------------
     Superuser: branch change → clear cache + reset + dropdown apply
     ------------------------- */
  if (els.branchSelect) {
    els.branchSelect.addEventListener("change", async () => {
      clearTableCache();
      resetInputSection();
      await ensureDropdownsOnAllRows();
    });
  }
}
