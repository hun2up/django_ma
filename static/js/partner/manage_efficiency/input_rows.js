// django_ma/static/js/partner/manage_efficiency/input_rows.js
//
// ✅ (기존 코드 유지) + reset 시 confirmGroupId도 같이 초기화
// ✅ amount 입력 시 콤마 + caret 유지
// ✅ content/amount 변화 시 tax 자동 계산
// ✅ user pick(검색모달) 이벤트 흡수

import { els } from "./dom_refs.js";
import { alertBox } from "./utils.js";
import { saveRows } from "./save.js";

const W = window;

function str(v) {
  return String(v ?? "").trim();
}
function $(id) {
  return document.getElementById(id);
}

function getField(row, name) {
  return row?.querySelector?.(`[name="${name}"]`) || null;
}
function getVal(row, name) {
  return str(getField(row, name)?.value ?? "");
}
function setVal(row, name, value) {
  const el = getField(row, name);
  if (el) el.value = value ?? "";
}

function getTaxField(row) {
  const candidates = ["tax", "tax_amount", "vat", "se_tax"];
  for (const n of candidates) {
    const el = getField(row, n);
    if (el) return el;
  }
  return null;
}

function clearRowInputs(row) {
  if (!row) return;

  row.querySelectorAll("input").forEach((el) => {
    if (el.type === "checkbox") el.checked = false;
    else el.value = "";
  });

  row.querySelectorAll("select").forEach((el) => {
    const hasEmpty = Array.from(el.options || []).some((o) => String(o.value) === "");
    el.value = hasEmpty ? "" : (el.options?.[0]?.value ?? "");
  });

  row.querySelectorAll("textarea").forEach((el) => (el.value = ""));
  row.dataset.searchTarget = "";
}

function getUser() {
  return W.currentUser || {};
}
function fillRequesterInfo(row) {
  const user = getUser();
  setVal(row, "rq_name", user.name || "");
  setVal(row, "rq_id", user.id || "");
  setVal(row, "rq_branch", user.branch || "");
}

/* amount comma */
function digitsOnly(v) {
  return str(v).replace(/[^\d]/g, "");
}
function formatWithCommaFromDigits(digits) {
  const d = str(digits);
  if (!d) return "";
  const normalized = d.replace(/^0+(?=\d)/, "");
  return normalized.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
function formatAmountValue(raw) {
  return formatWithCommaFromDigits(digitsOnly(raw));
}
function applyCommaFormatKeepCaret(inputEl) {
  const prev = str(inputEl.value);
  const caret = inputEl.selectionStart ?? prev.length;
  const leftDigitsCount = prev.slice(0, caret).replace(/[^\d]/g, "").length;

  const next = formatAmountValue(prev);
  inputEl.value = next;

  let newCaret = next.length;
  if (leftDigitsCount === 0) newCaret = 0;
  else {
    let count = 0;
    for (let i = 0; i < next.length; i++) {
      if (/\d/.test(next[i])) count++;
      if (count === leftDigitsCount) {
        newCaret = i + 1;
        break;
      }
    }
  }

  try {
    inputEl.setSelectionRange(newCaret, newCaret);
  } catch (_) {}
}

function attachAmountCommaFormatter() {
  if (W.__efficiencyAmountCommaBound) return;
  W.__efficiencyAmountCommaBound = true;

  const table = $("inputTable") || els.inputTable;
  if (!table) return;

  table.addEventListener("input", (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (el.name !== "amount") return;

    applyCommaFormatKeepCaret(el);

    const row = el.closest(".input-row");
    if (row) updateTaxForRow(row);
  });

  table.addEventListener("paste", (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (el.name !== "amount") return;

    e.preventDefault();
    const text = (e.clipboardData || W.clipboardData)?.getData("text") ?? "";
    el.value = formatAmountValue(text);

    requestAnimationFrame(() => {
      try {
        el.setSelectionRange(el.value.length, el.value.length);
      } catch (_) {}
      const row = el.closest(".input-row");
      if (row) updateTaxForRow(row);
    });
  });

  table.addEventListener(
    "blur",
    (e) => {
      const el = e.target;
      if (!(el instanceof HTMLInputElement)) return;
      if (el.name !== "amount") return;

      el.value = formatAmountValue(el.value);

      const row = el.closest(".input-row");
      if (row) updateTaxForRow(row);
    },
    true
  );
}

/* tax */
function calcTaxInt(amountInt) {
  return Math.floor(Number(amountInt || 0) * 0.033);
}
function formatIntComma(n) {
  const x = Number(n);
  if (!Number.isFinite(x) || x <= 0) return "0";
  return String(Math.trunc(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
function updateTaxForRow(row) {
  const taxEl = getTaxField(row);
  if (!taxEl) return;

  const amountDigits = digitsOnly(getVal(row, "amount"));
  const content = getVal(row, "content");

  // content 비었으면 세액도 비움(기존 UX 유지)
  if (!content) {
    taxEl.value = "";
    return;
  }

  const amountInt = parseInt(amountDigits || "0", 10);
  if (!Number.isFinite(amountInt) || amountInt <= 0) {
    taxEl.value = "";
    return;
  }

  taxEl.value = formatIntComma(calcTaxInt(amountInt));
}

function attachTaxAutoCalculator() {
  if (W.__efficiencyTaxAutoBound) return;
  W.__efficiencyTaxAutoBound = true;

  const table = $("inputTable") || els.inputTable;
  if (!table) return;

  table.addEventListener("input", (e) => {
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;
    const name = t.getAttribute("name") || "";
    if (name !== "content") return;

    const row = t.closest(".input-row");
    if (row) updateTaxForRow(row);
  });

  table.addEventListener(
    "blur",
    (e) => {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;

      const name = t.getAttribute("name") || "";
      if (name !== "content" && name !== "amount") return;

      const row = t.closest(".input-row");
      if (row) updateTaxForRow(row);
    },
    true
  );
}

/* user pick hooks */
function setActiveRowAndTarget(row, target) {
  if (!row) return;
  W.__efficiencyActiveRow = row;
  row.dataset.searchTarget = target;
  W.__efficiencyLastSearchTarget = target;
}

function extractSelectedUser(detail) {
  const d = detail || {};
  const u = d.user || d.selected || d.data || d.payload || d.result || d.item || d;

  const id = str(u.id || u.user_id || u.pk || u.emp_id || u.employee_id || u.userid || u.code || u.value || "");
  const name = str(
    u.name || u.username || u.full_name || u.emp_name || u.employee_name || u.user_name || u.label || u.text || ""
  );

  return { id, name };
}

function injectToRow(row, target, id, name) {
  if (!row) return false;
  if (!id && !name) return false;

  if (target === "ded") {
    setVal(row, "ded_name", name);
    setVal(row, "ded_id", id);
    return true;
  }
  if (target === "pay") {
    setVal(row, "pay_name", name);
    setVal(row, "pay_id", id);
    return true;
  }
  return false;
}

function attachUserPickHandlers() {
  if (W.__efficiencyUserPickBound) return;
  W.__efficiencyUserPickBound = true;

  const onPicked = (id, name) => {
    const row = W.__efficiencyActiveRow;
    if (!row) return;
    const target = str(row.dataset.searchTarget);
    injectToRow(row, target, id, name);
  };

  const eventHandler = (e) => {
    const { id, name } = extractSelectedUser(e?.detail);
    if (!id && !name) return;
    onPicked(id, name);
  };

  ["userSelected", "user-selected", "USER_SELECTED", "user_selected"].forEach((evt) => {
    document.addEventListener(evt, eventHandler);
    W.addEventListener(evt, eventHandler);
  });
}

/* reset */
export function resetInputSection() {
  const tbody = els.inputTable?.querySelector("tbody");
  if (!tbody) return;

  tbody.querySelectorAll(".input-row").forEach((r, i) => {
    if (i > 0) r.remove();
  });

  const firstRow = tbody.querySelector(".input-row");
  if (!firstRow) return;

  clearRowInputs(firstRow);
  fillRequesterInfo(firstRow);
  updateTaxForRow(firstRow);
}

function clearConfirmGroupUI() {
  if (els.confirmGroupId) els.confirmGroupId.value = "";
  if (els.confirmFileName) els.confirmFileName.value = "";
  if (els.confirmAttachmentId) els.confirmAttachmentId.value = "";
  if (els.confirmFileInput) els.confirmFileInput.value = "";
}

export function initInputRowEvents() {
  if (W.__efficiencyInputRowsBound) return;
  W.__efficiencyInputRowsBound = true;

  attachAmountCommaFormatter();
  attachTaxAutoCalculator();
  attachUserPickHandlers();

  document.addEventListener("click", (e) => {
    const dedBtn = e.target?.closest?.(".btnSearchDed");
    const payBtn = e.target?.closest?.(".btnSearchPay");
    if (!dedBtn && !payBtn) return;

    const btn = dedBtn || payBtn;
    const row = btn.closest(".input-row");
    if (!row) return;

    setActiveRowAndTarget(row, dedBtn ? "ded" : "pay");
  });

  els.btnAddRow?.addEventListener("click", () => {
    const tbody = els.inputTable?.querySelector("tbody");
    if (!tbody) return;

    const rows = tbody.querySelectorAll(".input-row");
    if (!rows.length) return;

    if (rows.length >= 10) {
      (alertBox || alert)("한 번에 최대 10건까지 입력 가능합니다.");
      return;
    }

    const newRow = rows[0].cloneNode(true);
    clearRowInputs(newRow);
    fillRequesterInfo(newRow);
    tbody.appendChild(newRow);
    updateTaxForRow(newRow);
  });

  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
    clearConfirmGroupUI();
  });

  document.addEventListener("click", (e) => {
    const btn = e.target?.closest?.(".btnRemoveRow");
    if (!btn) return;

    const row = btn.closest(".input-row");
    if (!row) return;

    const tbody = els.inputTable?.querySelector("tbody");
    const rows = tbody?.querySelectorAll(".input-row") || [];
    if (rows.length <= 1) {
      (alertBox || alert)("행이 하나뿐이라 삭제할 수 없습니다.");
      return;
    }
    row.remove();
  });

  els.btnSaveRows?.addEventListener("click", async () => {
    await saveRows();
  });

  const firstRow = els.inputTable?.querySelector(".input-row");
  if (firstRow) {
    fillRequesterInfo(firstRow);

    const amountEl = getField(firstRow, "amount");
    if (amountEl) amountEl.value = formatAmountValue(amountEl.value);

    updateTaxForRow(firstRow);
  }
}
