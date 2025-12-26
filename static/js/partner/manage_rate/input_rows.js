// django_ma/static/js/partner/manage_rate/input_rows.js
// ======================================================
// 📘 요율변경 요청 페이지 - 입력행 관리 (완성형)
// - superuser에서 branch 선택 후에도 드롭다운 미적용 되는 문제 해결
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { saveRows } from "./save.js";
import { fetchBranchTables, applyTableDropdownToRow, clearTableCache } from "./table_dropdown.js";

/* ==========================
   ✅ 공통: grade/branch
========================== */
function getGrade() {
  return String(els.root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

/**
 * ✅ superuser branch 값을 "확실히" 잡기
 * - 1순위: branchSelect.value
 * - 2순위: root.dataset.defaultBranch (혹시 세팅돼 있으면)
 * - 3순위: window.currentUser.branch (혹시 남아있으면)
 */
function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") {
    const v1 = String(els.branchSelect?.value || "").trim();
    const v2 = String(els.root?.dataset?.defaultBranch || "").trim();
    const v3 = String(window.currentUser?.branch || "").trim();
    return v1 || v2 || v3;
  }
  return String(window.currentUser?.branch || els.root?.dataset?.defaultBranch || "").trim();
}

/* ==========================
   ✅ 요청자 자동입력
========================== */
function fillRequesterInfo(row) {
  const u = window.currentUser || {};
  const rqName = row.querySelector('[name="rq_name"]');
  const rqId = row.querySelector('[name="rq_id"]');
  if (rqName) rqName.value = u.name || "";
  if (rqId) rqId.value = u.id || "";
}

/* ==========================
   ✅ 행 초기화
========================== */
function resetRowInputs(row) {
  row.querySelectorAll("input").forEach((el) => {
    el.value = "";
    el.readOnly = true;
  });

  row.querySelectorAll("select").forEach((sel) => {
    sel.value = "";
  });

  fillRequesterInfo(row);

  const memo = row.querySelector('[name="memo"]');
  if (memo) memo.readOnly = false;

  // 드롭다운 적용 전 대비(입력 허용)
  const aftF = row.querySelector('input[name="after_ftable"]');
  const aftL = row.querySelector('input[name="after_ltable"]');
  if (aftF) aftF.readOnly = false;
  if (aftL) aftL.readOnly = false;
}

/* ==========================
   ✅ active row 처리
========================== */
function setActiveRow(row) {
  els.inputTable?.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
  row.classList.add("active");
}

/* ==========================
   ✅ 대상자 상세정보 fetch
========================== */
async function fetchTargetDetail(targetId) {
  const base = String(els.root?.dataset?.targetDetailUrl || "").trim();
  const url = base
    ? new URL(base, window.location.origin)
    : new URL("/partner/ajax/rate-user-detail/", window.location.origin);

  url.searchParams.set("user_id", targetId);

  const res = await fetch(url.toString(), {
    headers: { "X-Requested-With": "XMLHttpRequest" },
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
  if (!branch) return; // superuser가 아직 지점 선택 안 했으면 여기서 종료

  const tables = await fetchBranchTables(branch);
  const rows = els.inputTable?.querySelectorAll("tbody tr.input-row") || [];
  rows.forEach((row) => applyTableDropdownToRow(row, tables));
}

/* ==========================
   ✅ 대상자 선택 시 자동입력 + 드랍박스 적용
========================== */
export async function fillTargetInfo(row, targetId) {
  const id = String(targetId || "").trim();
  if (!id) return;

  try {
    const { ok, data } = await fetchTargetDetail(id);
    if (!ok || data?.status !== "success") {
      return alertBox(data?.message || "대상자 정보를 불러오지 못했습니다.");
    }

    const info = data.data || {};

    // 요청자(비어있으면)
    const rqName = row.querySelector('[name="rq_name"]');
    const rqId = row.querySelector('[name="rq_id"]');
    if (rqName && !rqName.value) rqName.value = window.currentUser?.name || "";
    if (rqId && !rqId.value) rqId.value = window.currentUser?.id || "";

    const set = (name, val) => {
      const el = row.querySelector(`[name="${name}"]`);
      if (el) el.value = val ?? "";
    };

    set("tg_name", info.target_name || info.name || "");
    set("tg_id", info.target_id || info.id || "");

    set("before_ftable", info.non_life_table || "");
    set("before_frate", info.non_life_rate || "");

    set("before_ltable", info.life_table || "");
    set("before_lrate", info.life_rate || "");

    // ✅ 여기서 "현재 branch 기준" 드롭다운을 확실히 적용
    const branch = getEffectiveBranch();
    if (!branch) {
      // superuser가 branch 선택 안 했으면 안내
      if (getGrade() === "superuser") {
        alertBox("먼저 부서/지점을 선택한 뒤 대상자를 선택해주세요.");
      }
      return;
    }

    await ensureDropdownsOnAllRows();
  } catch (err) {
    console.error("❌ [rate] 대상자 정보 로드 실패:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}

/* ==========================
   ✅ 전체 초기화
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
   📘 초기화(이벤트 바인딩)
========================== */
export function initInputRowEvents() {
  if (!els.inputTable) return;

  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

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

    // ✅ 새 행도 바로 드롭다운 적용(지점 선택되어 있으면)
    await ensureDropdownsOnAllRows();
  });

  // ✅ 초기화
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
    // ✅ 초기화 후에도 지점 선택되어 있으면 드롭다운 다시 적용
    ensureDropdownsOnAllRows();
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
  document.addEventListener("userSelected", async (e) => {
    const targetId = e.detail?.id || e.detail?.user_id || e.detail?.pk;
    if (!targetId) return;

    const activeRow = tbody.querySelector(".input-row.active");
    if (!activeRow) return alertBox("대상자를 입력할 행을 먼저 클릭하세요.");

    showLoading("대상자 정보 불러오는 중...");
    await fillTargetInfo(activeRow, targetId);
    hideLoading();
  });

  // ✅ superuser 지점 변경 시: 캐시 초기화 + 입력 리셋 + 드롭다운 “미리 적용”
  if (els.branchSelect) {
    els.branchSelect.addEventListener("change", async () => {
      clearTableCache();
      resetInputSection();
      await ensureDropdownsOnAllRows(); // ⭐ superuser에서 이게 없으면 다시 input으로 남는 케이스가 생김
    });
  }
}
