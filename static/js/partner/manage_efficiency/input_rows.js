// django_ma/static/js/partner/manage_efficiency/input_rows.js
//
// ✅ Final Refactor (2025-12-31 + tax)
// - ded/pay 모달 주입 “100% 보장” (event + click-hook)
// - amount: 숫자만 + 천단위 콤마 + 커서 유지
// - ✅ tax: content 입력(또는 amount 변경) 시 tax = floor(amount * 0.033) 자동 표시 (콤마 포함)
// - payload: category/amount/ded*/pay*/content (efficiency schema 유지: tax는 화면표시용)
// - URL/CSRF/응답파싱 안정화 + saved_count===0 안내
//
// IMPORTANT
// - import 경로에 ?v= 절대 붙이지 마세요. (템플릿 script src에서만 v 사용)

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";

console.log("✅ efficiency/input_rows.js LOADED", {
  build: "2025-12-31-efficiency-inputrows-final-tax-refactor",
  url: import.meta?.url,
});

const W = window;

/* =======================================================
   0) small utils
======================================================= */
function str(v) {
  return String(v ?? "").trim();
}
function info(...args) {
  console.log("[efficiency/input_rows]", ...args);
}
function warn(...args) {
  console.warn("[efficiency/input_rows]", ...args);
}
function $(id) {
  return document.getElementById(id);
}

/* =======================================================
   1) Dataset helpers
======================================================= */
function dsUrl(keys = []) {
  const ds = els.root?.dataset;
  if (!ds) return "";
  for (const k of keys) {
    const v = ds[k];
    if (v && String(v).trim()) return String(v).trim();
  }
  return "";
}

function getSaveUrlFromDataset() {
  // manage_calculate.html: data-data-save-url -> dataset: dataDataSaveUrl
  return dsUrl(["saveUrl", "dataSaveUrl", "dataDataSaveUrl", "dataDataSave", "dataSave"]);
}

function getUser() {
  return W.currentUser || {};
}

function getBoot() {
  return W.ManageefficiencyBoot || {};
}

/* =======================================================
   2) Controls helpers (year/month/branch)
======================================================= */
function getYearValue() {
  return str(els.year?.value || $("yearSelect")?.value);
}

function getMonthValue() {
  return str(els.month?.value || $("monthSelect")?.value);
}

function getYM() {
  const y = getYearValue();
  const m = getMonthValue();
  if (!y || !m) return "";
  return `${y}-${String(m).padStart(2, "0")}`;
}

function getEffectiveBranch() {
  const user = getUser();
  const grade = str(user.grade);

  if (grade === "superuser") {
    const v = str(els.branch?.value || $("branchSelect")?.value);
    return v || "-";
  }
  return str(user.branch || "-") || "-";
}

/* =======================================================
   3) DOM helpers
======================================================= */
function getField(row, name) {
  return row?.querySelector?.(`[name="${name}"]`) || null; // input/select/textarea
}

function getVal(row, name) {
  return str(getField(row, name)?.value ?? "");
}

function setVal(row, name, value) {
  const el = getField(row, name);
  if (!el) return;
  el.value = value ?? "";
}

function getTaxField(row) {
  // 템플릿 name이 무엇이든 흡수하도록 후보들 지원
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

/* =======================================================
   4) 요청자 자동입력 (표시용)
======================================================= */
function fillRequesterInfo(row) {
  const user = getUser();
  setVal(row, "rq_name", user.name || "");
  setVal(row, "rq_id", user.id || "");
  setVal(row, "rq_branch", user.branch || "");
}

/* =======================================================
   5) amount: 숫자만 + 콤마 (커서 유지)
======================================================= */
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

/**
 * ✅ amount 변경에 의해 tax도 같이 갱신되어야 함
 * - 단, 여기서는 "커서/콤마"만 처리하고 tax 갱신은 updateTaxForRow로 위임
 */
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

    // ✅ amount 입력 도중에도 tax 즉시 갱신
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

/* =======================================================
   5.5) ✅ tax 계산/표시
   - 내용(content) 입력/변경 시
   - 금액(amount) 변경 시
   tax = floor(amount * 0.033)
   표시: 콤마 포함
======================================================= */
function calcTaxInt(amountInt) {
  return Math.floor(Number(amountInt || 0) * 0.033);
}

function formatIntComma(n) {
  const x = Number(n);
  if (!Number.isFinite(x) || x <= 0) return "0";
  return String(Math.trunc(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * ✅ 요구사항 반영:
 * - "내용 입력시" 표시하고 싶음
 * - amount가 바뀌어도, content가 비어있으면 tax는 비움
 * - content가 있고 amount가 유효하면 tax 표시
 */
function updateTaxForRow(row) {
  if (!row) return;
  const taxEl = getTaxField(row);
  if (!taxEl) return; // 템플릿에 tax input이 없으면 패스

  const amountDigits = digitsOnly(getVal(row, "amount"));
  const content = getVal(row, "content");

  // 내용이 없으면 표시하지 않음(요구사항)
  if (!content) {
    taxEl.value = "";
    return;
  }

  const amountInt = parseInt(amountDigits || "0", 10);
  if (!Number.isFinite(amountInt) || amountInt <= 0) {
    taxEl.value = "";
    return;
  }

  const taxInt = calcTaxInt(amountInt);
  taxEl.value = formatIntComma(taxInt);
}

function attachTaxAutoCalculator() {
  if (W.__efficiencyTaxAutoBound) return;
  W.__efficiencyTaxAutoBound = true;

  const table = $("inputTable") || els.inputTable;
  if (!table) return;

  // content는 input 이벤트가 가장 자연스러움
  table.addEventListener("input", (e) => {
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;

    const name = t.getAttribute("name") || "";
    if (name !== "content") return;

    const row = t.closest(".input-row");
    if (!row) return;

    updateTaxForRow(row);
  });

  // amount는 comma formatter에서 이미 갱신하므로 여기서는 blur만 보조
  table.addEventListener(
    "blur",
    (e) => {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;

      const name = t.getAttribute("name") || "";
      if (name !== "content" && name !== "amount") return;

      const row = t.closest(".input-row");
      if (!row) return;

      updateTaxForRow(row);
    },
    true
  );
}

/* =======================================================
   6) ded/pay 타겟 설정 + 선택 사용자 추출/주입
======================================================= */
function setActiveRowAndTarget(row, target /* "ded" | "pay" */) {
  if (!row) return;
  W.__efficiencyActiveRow = row;
  row.dataset.searchTarget = target;
  W.__efficiencyLastSearchTarget = target;
}

function extractSelectedUser(detail) {
  const d = detail || {};
  const u = d.user || d.selected || d.data || d.payload || d.result || d.item || d;

  const id = str(
    u.id ||
      u.user_id ||
      u.pk ||
      u.emp_id ||
      u.employee_id ||
      u.userid ||
      u.code ||
      u.value ||
      ""
  );

  const name = str(
    u.name ||
      u.username ||
      u.full_name ||
      u.emp_name ||
      u.employee_name ||
      u.user_name ||
      u.label ||
      u.text ||
      ""
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

  const onPicked = (id, name, source = "unknown") => {
    const row = W.__efficiencyActiveRow;
    if (!row) return;

    const target = str(row.dataset.searchTarget);
    const ok = injectToRow(row, target, id, name);

    if (!ok) warn("picked but target missing", { source, target, id, name });
    else info("✅ injected", { source, target, id, name });
  };

  // A) 이벤트 기반
  const eventHandler = (e) => {
    const { id, name } = extractSelectedUser(e?.detail);
    if (!id && !name) return;
    onPicked(id, name, "event");
  };

  ["userSelected", "user-selected", "USER_SELECTED", "user_selected"].forEach((evt) => {
    document.addEventListener(evt, eventHandler);
    W.addEventListener(evt, eventHandler);
  });

  // B) 클릭 훅 기반(이벤트가 안 오는 환경 커버)
  document.addEventListener("click", (e) => {
    const modal = $("searchUserModal");
    if (!modal) return;
    if (!modal.contains(e.target)) return;

    const candidate =
      e.target.closest("[data-id]") ||
      e.target.closest("[data-user-id]") ||
      e.target.closest("[data-code]") ||
      e.target.closest("[data-name]") ||
      e.target.closest(".btnSelectUser") ||
      e.target.closest(".btn-select") ||
      e.target.closest(".select-user") ||
      e.target.closest("button");

    if (!candidate) return;

    const txt = str(candidate.textContent);
    const looksLikeSelect =
      candidate.classList.contains("btnSelectUser") ||
      candidate.classList.contains("btn-select") ||
      candidate.classList.contains("select-user") ||
      /선택|적용|등록|확인/i.test(txt);

    if (!looksLikeSelect) return;

    const id = str(
      candidate.dataset.id ||
        candidate.dataset.userId ||
        candidate.dataset.code ||
        candidate.getAttribute("data-id") ||
        candidate.getAttribute("data-user-id") ||
        candidate.getAttribute("data-code") ||
        ""
    );

    const name = str(
      candidate.dataset.name ||
        candidate.dataset.userName ||
        candidate.dataset.label ||
        candidate.getAttribute("data-name") ||
        candidate.getAttribute("data-user-name") ||
        ""
    );

    const finalId = id || str(candidate.value);
    const finalName = name || txt.replace(/\s+/g, " ");

    if (!finalId && !finalName) return;
    onPicked(finalId, finalName, "click-hook");
  });
}

/* =======================================================
   7) 입력 초기화
======================================================= */
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

  // ✅ 초기화 후 세액도 정리
  updateTaxForRow(firstRow);
}

/* =======================================================
   8) payload 구성 (efficiency schema 유지: tax는 화면 표시용)
======================================================= */
function collectValidRows() {
  const tbody = els.inputTable?.querySelector("tbody");
  const rows = tbody?.querySelectorAll(".input-row") || [];
  const valid = [];

  rows.forEach((row, idx) => {
    const category = getVal(row, "category");
    const amountView = getVal(row, "amount"); // "1,234"
    const amountDigits = digitsOnly(amountView); // "1234"
    const content = getVal(row, "content");

    const hasAny =
      !!category ||
      !!amountDigits ||
      !!content ||
      !!getVal(row, "ded_id") ||
      !!getVal(row, "pay_id");

    if (!hasAny) return;

    if (!category) throw new Error(`(${idx + 1}행) 구분을 선택해주세요.`);
    if (!amountDigits) throw new Error(`(${idx + 1}행) 금액을 입력해주세요.`);

    const amount = parseInt(amountDigits, 10);
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new Error(`(${idx + 1}행) 금액은 1 이상의 정수만 가능합니다.`);
    }

    if (!content) throw new Error(`(${idx + 1}행) 내용을 입력해주세요.`);

    valid.push({
      category,
      amount,
      ded_name: getVal(row, "ded_name"),
      ded_id: getVal(row, "ded_id"),
      pay_name: getVal(row, "pay_name"),
      pay_id: getVal(row, "pay_id"),
      content,
    });
  });

  return valid;
}

/* =======================================================
   9) 저장 + 갱신
======================================================= */
function resolveSaveUrl() {
  const boot = getBoot();

  const dsSave = getSaveUrlFromDataset();
  const attrSave = str(els.root?.getAttribute("data-data-save-url"));
  const bootSave = str(boot.dataSaveUrl);

  const final = dsSave || attrSave || bootSave;

  console.log("🧩 [efficiency] saveUrl resolved:", {
    dsSave,
    attrSave,
    bootSave,
    final,
    rootDataset: els.root?.dataset,
  });

  return final;
}

function safeParseJson(text) {
  const t = str(text);
  if (!t) return {};
  try {
    return JSON.parse(t);
  } catch {
    return {};
  }
}

async function saveRowsToServer() {
  const user = getUser();
  const ym = getYM();
  const branch = getEffectiveBranch();

  if (!ym) {
    (alertBox || alert)("연도/월도를 확인해주세요.");
    return;
  }

  let validRows = [];
  try {
    validRows = collectValidRows();
  } catch (err) {
    (alertBox || alert)(err?.message || "입력값을 확인해주세요.");
    return;
  }

  if (!validRows.length) {
    (alertBox || alert)("입력된 데이터가 없습니다.");
    return;
  }

  const saveUrl = resolveSaveUrl();
  if (!saveUrl) {
    console.error("[efficiency/input_rows] saveUrl 누락", els.root?.dataset, getBoot());
    (alertBox || alert)("저장 URL이 없습니다. (data-data-save-url / boot.dataSaveUrl 확인)");
    return;
  }

  const payload = {
    month: ym,
    rows: validRows,
    part: user.part || "-",
    branch,
  };

  showLoading("저장 중입니다...");
  try {
    const res = await fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload),
    });

    const text = await res.text();
    const data = safeParseJson(text);

    if (!res.ok || data.status !== "success") {
      console.error("❌ 저장 실패 응답:", { status: res.status, text, data });
      (alertBox || alert)(data.message || `저장에 실패했습니다. (${res.status})`);
      return;
    }

    if (Number(data?.saved_count ?? -1) === 0) {
      (alertBox || alert)(
        "⚠️ 저장된 건수가 0건입니다.\n서버 EfficiencyChange 스키마/저장 로직이 프론트 payload와 일치하는지 확인하세요."
      );
    } else {
      (alertBox || alert)(data.message || `저장 완료! (${data.saved_count}건)`);
    }

    resetInputSection();
    await fetchData(ym, branch);
  } catch (err) {
    console.error("❌ 저장 실패:", err);
    (alertBox || alert)(err?.message || "저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}

/* =======================================================
   10) 이벤트 초기화 (외부에서 호출)
======================================================= */
export function initInputRowEvents() {
  if (W.__efficiencyInputRowsBound) return;
  W.__efficiencyInputRowsBound = true;

  attachAmountCommaFormatter();
  attachTaxAutoCalculator(); // ✅ 세액 자동 계산
  attachUserPickHandlers();

  // 공제자/지급자 검색 버튼 클릭 → activeRow/target 설정 (위임)
  document.addEventListener("click", (e) => {
    const dedBtn = e.target?.closest?.(".btnSearchDed");
    const payBtn = e.target?.closest?.(".btnSearchPay");
    if (!dedBtn && !payBtn) return;

    const btn = dedBtn || payBtn;
    const row = btn.closest(".input-row");
    if (!row) return;

    setActiveRowAndTarget(row, dedBtn ? "ded" : "pay");
  });

  // 행 추가
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

    // ✅ 새 행도 세액 초기화
    updateTaxForRow(newRow);
  });

  // 초기화
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // 행 삭제(위임)
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

  // 저장
  els.btnSaveRows?.addEventListener("click", async () => {
    await saveRowsToServer();
  });

  // 최초 요청자 주입 + 금액/세액 초기 포맷
  const firstRow = els.inputTable?.querySelector(".input-row");
  if (firstRow) {
    fillRequesterInfo(firstRow);

    const amountEl = getField(firstRow, "amount");
    if (amountEl) amountEl.value = formatAmountValue(amountEl.value);

    updateTaxForRow(firstRow);
  }
}
