// django_ma/static/js/partner/manage_efficiency/input_rows.js
//
// ✅ Refactor (2025-12-29) — ded/pay 모달 주입 “100% 보장” + 금액 콤마 자동삽입
// ------------------------------------------------------------------
// 목표
// 1) 공제자/지급자 검색 버튼 각각 → 같은 모달을 열되,
//    선택 결과를 'ded_*' 또는 'pay_*'에 정확히 주입
// 2) 공통 모달 구현 차이(userSelected 이벤트/DOM 클릭 방식) 모두 대응
// 3) 금액(amount) 숫자만 허용 + 천단위 콤마 자동 삽입 + 커서 유지
// 4) row clone/초기화/삭제/저장/URL/CSRF/응답파싱 안정화
//
// 전제
// - 템플릿 inputTable 버튼 클래스:
//    .btnSearchDed (공제자 검색), .btnSearchPay (지급자 검색)
// - 입력 필드 name:
//    rq_name,rq_id,rq_branch, category(select), amount(input), ded_name,ded_id, pay_name,pay_id, content
// - 모달: #searchUserModal (components/search_user_modal.html)
//
// IMPORTANT
// - import 경로에 ?v= 절대 붙이지 마세요. (템플릿 script src에서만 v 사용)

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";

console.log("✅ efficiency/input_rows.js LOADED", {
  build: "2025-12-29-efficiency-inputrows-refactor-amount-comma",
  url: import.meta?.url,
});

/* =======================================================
   0) 작은 유틸
======================================================= */
const W = window;

function str(v) {
  return String(v ?? "").trim();
}

function warn(...args) {
  console.warn("[efficiency/input_rows]", ...args);
}

function info(...args) {
  console.log("[efficiency/input_rows]", ...args);
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
  return str(els.year?.value || document.getElementById("yearSelect")?.value);
}

function getMonthValue() {
  return str(els.month?.value || document.getElementById("monthSelect")?.value);
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

  // superuser는 선택 지점 우선
  if (grade === "superuser") {
    const v = str(els.branch?.value || document.getElementById("branchSelect")?.value);
    return v || "-";
  }

  // 그 외는 로그인 사용자 지점
  return str(user.branch || "-") || "-";
}

/* =======================================================
   3) DOM helpers
======================================================= */
function getField(row, name) {
  return row?.querySelector?.(`[name="${name}"]`) || null; // input/select 모두
}

function getVal(row, name) {
  return str(getField(row, name)?.value ?? "");
}

function setVal(row, name, value) {
  const el = getField(row, name);
  if (!el) return;
  el.value = value ?? "";
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

  row.dataset.searchTarget = "";
}

/* =======================================================
   4) 요청자 자동입력
======================================================= */
function fillRequesterInfo(row) {
  const user = getUser();
  setVal(row, "rq_name", user.name || "");
  setVal(row, "rq_id", user.id || "");
  setVal(row, "rq_branch", user.branch || "");
}

/* =======================================================
   5) amount: 숫자만 + 천단위 콤마 자동 삽입 (커서 유지)
======================================================= */
function digitsOnly(v) {
  return str(v).replace(/[^\d]/g, "");
}

function formatWithCommaFromDigits(digits) {
  const d = str(digits);
  if (!d) return "";
  const normalized = d.replace(/^0+(?=\d)/, ""); // "00012" -> "12"
  return normalized.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatAmountValue(raw) {
  return formatWithCommaFromDigits(digitsOnly(raw));
}

function applyCommaFormatKeepCaret(inputEl) {
  const prev = str(inputEl.value);
  const caret = inputEl.selectionStart ?? prev.length;

  // caret 왼쪽의 '숫자 개수'
  const leftDigitsCount = prev.slice(0, caret).replace(/[^\d]/g, "").length;

  const next = formatAmountValue(prev);
  inputEl.value = next;

  // leftDigitsCount만큼 숫자가 나오는 위치를 찾아 caret 복원
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

  const table = document.getElementById("inputTable") || els.inputTable;
  if (!table) return;

  // 실시간 포맷 (행 추가/복제 대응: 이벤트 위임)
  table.addEventListener("input", (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (el.name !== "amount") return;
    applyCommaFormatKeepCaret(el);
  });

  // 붙여넣기 대응
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
    });
  });

  // 포커스 아웃 시 정리
  table.addEventListener(
    "blur",
    (e) => {
      const el = e.target;
      if (!(el instanceof HTMLInputElement)) return;
      if (el.name !== "amount") return;
      el.value = formatAmountValue(el.value);
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
  W.__efficiencyLastSearchTarget = target; // 디버그용
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

  // A) 이벤트 기반 (common/search_user_modal.js가 userSelected를 쏘는 경우)
  const eventHandler = (e) => {
    const { id, name } = extractSelectedUser(e?.detail);
    if (!id && !name) return;
    onPicked(id, name, "event");
  };

  ["userSelected", "user-selected", "USER_SELECTED", "user_selected"].forEach((evt) => {
    document.addEventListener(evt, eventHandler);
    W.addEventListener(evt, eventHandler);
  });

  // B) 클릭 훅 기반 (이벤트가 안 오는 환경 100% 커버)
  document.addEventListener("click", (e) => {
    const modal = document.getElementById("searchUserModal");
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
}

/* =======================================================
   8) payload 구성 (NEW schema)
   - amount는 "콤마 제거 후 정수"로 전송
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

    // 완전 빈 행은 무시
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

    (alertBox || alert)(data.message || "저장 완료!");
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
  attachUserPickHandlers();

  // ✅ 공제자/지급자 검색 버튼 클릭 → activeRow/target 설정 (이벤트 위임)
  document.addEventListener("click", (e) => {
    const dedBtn = e.target?.closest?.(".btnSearchDed");
    const payBtn = e.target?.closest?.(".btnSearchPay");
    if (!dedBtn && !payBtn) return;

    const btn = dedBtn || payBtn;
    const row = btn.closest(".input-row");
    if (!row) return;

    setActiveRowAndTarget(row, dedBtn ? "ded" : "pay");
  });

  // ✅ 행 추가
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
  });

  // ✅ 초기화
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // ✅ 행 삭제 (위임)
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

  // ✅ 저장
  els.btnSaveRows?.addEventListener("click", async () => {
    await saveRowsToServer();
  });

  // ✅ 최초 요청자 주입 + 금액 초기 포맷(혹시 기본값 있으면)
  const firstRow = els.inputTable?.querySelector(".input-row");
  if (firstRow) {
    fillRequesterInfo(firstRow);
    const amountEl = getField(firstRow, "amount");
    if (amountEl) amountEl.value = formatAmountValue(amountEl.value);
  }
}
