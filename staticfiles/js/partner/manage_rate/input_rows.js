// django_ma/static/js/partner/manage_rate/input_rows.js
// ======================================================
// 📘 요율변경 요청 페이지 - 입력행 관리 (FINAL)
// - 요청자/대상자 컬럼 통합 UI 대응 (rq_display / tg_display)
// - superuser에서 branch 선택 후에도 드롭다운 미적용 되는 문제 해결
// - 행 추가/삭제/초기화/저장 버튼 바인딩 + 모달 선택 이벤트 처리
// - 중복 바인딩 방지(페이지 BFCache/재진입 안전)
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { saveRows } from "./save.js";
import {
  fetchBranchTables,
  applyTableDropdownToRow,
  clearTableCache,
} from "./table_dropdown.js";

/* ==========================
   ✅ Utils
========================== */
function toStr(v) {
  return String(v ?? "").trim();
}

function fmtPerson(name, id) {
  const n = toStr(name);
  const i = toStr(id);
  if (n && i) return `${n}(${i})`;
  return n || i || "";
}

/* ==========================
   ✅ grade/branch helpers
========================== */
function getGrade() {
  return toStr(els.root?.dataset?.userGrade || window.currentUser?.grade);
}

/**
 * ✅ superuser branch 값을 "확실히" 잡기
 * - 1순위: branchSelect.value
 * - 2순위: root.dataset.defaultBranch
 * - 3순위: window.currentUser.branch
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

/* ==========================
   ✅ Requester auto-fill
   - rq_display + hidden rq_name/rq_id
========================== */
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

/* ==========================
   ✅ Row reset
========================== */
function resetRowInputs(row) {
  // input 초기화 (checkbox는 안전 처리)
  row.querySelectorAll("input").forEach((el) => {
    if (el.type === "checkbox") {
      el.checked = false;
      return;
    }
    el.value = "";
    el.readOnly = true; // 기본은 readonly로 잠금 (필요한 필드만 아래에서 해제)
  });

  // select 초기화
  row.querySelectorAll("select").forEach((sel) => {
    sel.value = "";
  });

  // 요청자 자동 입력 + 표시
  fillRequesterInfo(row);

  // memo는 입력 가능
  const memo = row.querySelector('[name="memo"]');
  if (memo) memo.readOnly = false;

  // 드롭다운 적용 전 대비(입력 허용)
  const aftF = row.querySelector('input[name="after_ftable"]');
  const aftL = row.querySelector('input[name="after_ltable"]');
  if (aftF) aftF.readOnly = false;
  if (aftL) aftL.readOnly = false;

  // 표시용 display는 항상 readonly 유지
  const rqDisp = row.querySelector(".rq_display");
  const tgDisp = row.querySelector(".tg_display");
  if (rqDisp) rqDisp.readOnly = true;
  if (tgDisp) tgDisp.readOnly = true;
}

/* ==========================
   ✅ Active row (for modal)
========================== */
function setActiveRow(row) {
  els.inputTable?.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
  row.classList.add("active");
}

/* ==========================
   ✅ Target detail fetch
========================== */
async function fetchTargetDetail(targetId) {
  const base = toStr(els.root?.dataset?.targetDetailUrl);
  const url = base
    ? new URL(base, window.location.origin)
    : new URL("/partner/ajax/rate-user-detail/", window.location.origin);

  url.searchParams.set("user_id", toStr(targetId));

  const res = await fetch(url.toString(), {
    headers: { "X-Requested-With": "XMLHttpRequest" },
    credentials: "same-origin",
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = { status: "error", message: "JSON 파싱 실패" };
  }

  return { ok: res.ok, data };
}

/* ==========================
   ✅ (핵심) 현재 branch 기준 테이블 목록 로드 후
   모든 입력행에 드롭다운 강제 적용
========================== */
async function ensureDropdownsOnAllRows() {
  const branch = getEffectiveBranch();
  if (!branch) return; // superuser가 아직 지점 선택 안 했으면 종료

  const tables = await fetchBranchTables(branch);
  const rows = els.inputTable?.querySelectorAll("tbody tr.input-row") || [];
  rows.forEach((row) => applyTableDropdownToRow(row, tables));
}

/* ==========================
   ✅ Target fill + dropdown apply
   - tg_display + hidden tg_name/tg_id
========================== */
export async function fillTargetInfo(row, targetId) {
  const id = toStr(targetId);
  if (!id) return;

  try {
    const { ok, data } = await fetchTargetDetail(id);
    if (!ok || data?.status !== "success") {
      return alertBox(data?.message || "대상자 정보를 불러오지 못했습니다.");
    }

    const info = data.data || {};

    // 요청자(비어있으면) 채움 + rq_display도 갱신
    const rqNameEl = row.querySelector('[name="rq_name"]');
    const rqIdEl = row.querySelector('[name="rq_id"]');
    if (rqNameEl && !toStr(rqNameEl.value)) rqNameEl.value = toStr(window.currentUser?.name);
    if (rqIdEl && !toStr(rqIdEl.value)) rqIdEl.value = toStr(window.currentUser?.id);
    const rqDispEl = row.querySelector(".rq_display");
    if (rqDispEl) rqDispEl.value = fmtPerson(toStr(rqNameEl?.value), toStr(rqIdEl?.value));

    // 안전 setter
    const set = (name, val) => {
      const el = row.querySelector(`[name="${name}"]`);
      if (el) el.value = val ?? "";
    };

    // ✅ 대상자 hidden
    const tgName = toStr(info.target_name || info.name);
    const tgId = toStr(info.target_id || info.id);
    set("tg_name", tgName);
    set("tg_id", tgId);

    // ✅ 대상자 display
    const tgDisp = row.querySelector(".tg_display");
    if (tgDisp) tgDisp.value = fmtPerson(tgName, tgId);

    // 변경전 테이블/요율
    set("before_ftable", info.non_life_table || "");
    set("before_frate", info.non_life_rate || "");
    set("before_ltable", info.life_table || "");
    set("before_lrate", info.life_rate || "");

    // ✅ branch 체크 (superuser는 branch 먼저)
    const branch = getEffectiveBranch();
    if (!branch) {
      if (getGrade() === "superuser") {
        alertBox("먼저 부서/지점을 선택한 뒤 대상자를 선택해주세요.");
      }
      return;
    }

    // ✅ 현재 branch 기준 드롭다운 강제 적용
    await ensureDropdownsOnAllRows();
  } catch (err) {
    console.error("❌ [rate/input_rows] 대상자 정보 로드 실패:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}

/* ==========================
   ✅ Reset input section
========================== */
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

/* ==========================
   📘 Init bindings (once)
========================== */
let bound = false;

export function initInputRowEvents() {
  if (bound) return;
  bound = true;

  if (!els.inputTable) return;

  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

  // 최초 행 초기화
  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    resetRowInputs(firstRow);
    setActiveRow(firstRow);
  }

  // ✅ 행 추가
  els.btnAddRow?.addEventListener("click", async () => {
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length >= 10) return alertBox("대상자는 한 번에 10명까지 입력 가능합니다.");

    const newRow = rows[0].cloneNode(true);
    resetRowInputs(newRow);
    tbody.appendChild(newRow);
    setActiveRow(newRow);

    // 지점 선택되어 있으면 즉시 드롭다운 적용
    await ensureDropdownsOnAllRows();
  });

  // ✅ 초기화
  els.btnResetRows?.addEventListener("click", async () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
    await ensureDropdownsOnAllRows();
  });

  // ✅ 저장
  els.btnSaveRows?.addEventListener("click", () => {
    saveRows();
  });

  // ✅ 테이블 내부 이벤트 위임 (삭제 / active 처리)
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

  // ✅ 모달에서 사용자 선택 이벤트
  // - 공용 모달은 document/window 둘 다 dispatch할 수 있어 document로 수신 유지
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

  // ✅ superuser 지점 변경 시: 캐시 초기화 + 입력 리셋 + 드롭다운 미리 적용
  if (els.branchSelect) {
    els.branchSelect.addEventListener("change", async () => {
      clearTableCache();
      resetInputSection();
      await ensureDropdownsOnAllRows(); // ⭐ input으로 남는 케이스 방지
    });
  }
}
