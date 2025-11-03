// django_ma/static/js/partner/manage_rate/input_rows.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";

/* =======================================================
   📘 입력 행 관련 초기화
   ======================================================= */
export function initInputRowEvents() {
  // 행 추가
  els.btnAddRow?.addEventListener("click", () => {
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length >= 10) {
      alertBox("대상자는 한 번에 10명까지 입력 가능합니다.");
      return;
    }

    const newRow = rows[0].cloneNode(true);
    newRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
      el.readOnly = true;
    });

    fillRequesterInfo(newRow);
    allowEditableFields(newRow);
    tbody.appendChild(newRow);
  });

  // 초기화
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // 삭제 (위임)
  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("btnRemoveRow")) return;
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length <= 1) {
      alertBox("행이 하나뿐이라 삭제할 수 없습니다.");
      return;
    }
    e.target.closest(".input-row").remove();
  });

  // 행 클릭 시 active
  document.addEventListener("click", (e) => {
    const tr = e.target.closest(".input-row");
    if (!tr) return;
    els.inputTable.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    tr.classList.add("active");
  });

  // 첫 행 세팅
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => (el.readOnly = true));
    fillRequesterInfo(firstRow);
    allowEditableFields(firstRow);
    firstRow.classList.add("active");
  }

  // 공통 모달에서 선택된 사용자 받기 → 여기서 상세조회
  document.addEventListener("userSelected", async (e) => {
    const targetId = e.detail?.id;
    if (!targetId) return;

    const activeRow = els.inputTable.querySelector(".input-row.active");
    if (!activeRow) {
      alertBox("대상자를 입력할 행을 먼저 클릭하세요.");
      return;
    }

    showLoading("대상자 정보 불러오는 중...");
    await fillTargetInfo(activeRow, targetId);
    hideLoading();
  });

  // (레거시) .btn-select-user 처리
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".btn-select-user");
    if (!btn) return;

    const targetId = btn.dataset.id;
    const activeRow = els.inputTable.querySelector(".input-row.active");
    if (!activeRow || !targetId) {
      alertBox("대상자를 입력할 행을 먼저 클릭하세요.");
      return;
    }

    showLoading("대상자 정보 불러오는 중...");
    await fillTargetInfo(activeRow, targetId);
    hideLoading();

    const modalEl = document.getElementById("searchUserModal");
    if (modalEl) {
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();
    }
  });
}

/* =======================================================
   ✅ 요청자 정보 자동입력
   ======================================================= */
function fillRequesterInfo(row) {
  const user = window.currentUser || {};
  const rqName = row.querySelector('input[name="rq_name"]');
  if (rqName) rqName.value = user.name || "";
  const rqId = row.querySelector('input[name="rq_id"]');
  if (rqId) rqId.value = user.id || "";
  const rqBranch = row.querySelector('input[name="rq_branch"]');
  if (rqBranch) rqBranch.value = user.branch || "";
}

/* =======================================================
   ✅ 전체 입력 초기화
   ======================================================= */
export function resetInputSection() {
  const tbody = els.inputTable.querySelector("tbody");
  tbody.querySelectorAll(".input-row").forEach((r, i) => {
    if (i > 0) r.remove();
  });
  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
      el.readOnly = true;
    });
    fillRequesterInfo(firstRow);
    allowEditableFields(firstRow);
    firstRow.classList.add("active");
  }
}

/* =======================================================
   ✅ 수정 가능한 칸만 풀어주기
   (템플릿: after_ftable, after_ltable, memo)
   ======================================================= */
function allowEditableFields(row) {
  ["after_ftable", "after_ltable", "memo"].forEach((name) => {
    const el = row.querySelector(`input[name="${name}"]`);
    if (el) el.readOnly = false;
  });
}

/* =======================================================
   ✅ 대상자 상세 불러오기 (하이픈 → 언더스코어 fallback)
   ======================================================= */
async function fetchTargetDetail(targetId) {
  // 1차: /partner/ajax/rate-user-detail/
  const url1 = `/partner/ajax/rate-user-detail/?user_id=${encodeURIComponent(targetId)}`;
  const res1 = await fetch(url1, { headers: { "X-Requested-With": "XMLHttpRequest" } });
  if (res1.ok) {
    return res1.json();
  }

  // 2차: /partner/ajax_rate_user_detail/
  const url2 = `/partner/ajax_rate_user_detail/?user_id=${encodeURIComponent(targetId)}`;
  const res2 = await fetch(url2, { headers: { "X-Requested-With": "XMLHttpRequest" } });
  return res2.json();
}

/* =======================================================
   ✅ 대상자 선택 후 자동입력
   ======================================================= */
export async function fillTargetInfo(row, targetId) {
  try {
    const data = await fetchTargetDetail(targetId);
    if (data.status !== "success") {
      alertBox(data.message || "대상자 정보를 불러오지 못했습니다.");
      return;
    }

    const info = data.data || {};

    // 기본 정보
    row.querySelector('input[name="tg_name"]').value = info.target_name || "";
    row.querySelector('input[name="tg_id"]').value = info.target_id || "";

    // 기존 테이블/요율 (변경전)
    row.querySelector('input[name="before_ftable"]').value = info.non_life_table || "";
    row.querySelector('input[name="before_frate"]').value = info.non_life_rate || "";
    row.querySelector('input[name="before_ltable"]').value = info.life_table || "";
    row.querySelector('input[name="before_lrate"]').value = info.life_rate || "";

    // 변경후 테이블 선택 드롭다운으로 전환
    await loadTableDropdowns(row);

  } catch (err) {
    console.error("❌ 대상자 정보 로드 실패:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}

/* =======================================================
   ✅ 요청자 branch 기준 테이블 목록 불러오기
   ======================================================= */
async function loadTableDropdowns(row) {
  const branch = window.currentUser?.branch || "";
  if (!branch) return;

  try {
    const res = await fetch(`/partner/ajax_table_fetch/?branch=${encodeURIComponent(branch)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await res.json();
    const tables = data.rows || [];

    // 테이블 옵션 HTML 구성
    const options = tables
      .map(t => `<option value="${t.table || t.table_name}">${t.table || t.table_name}</option>`)
      .join("");

    // 손보 select
    const fTableCell = row.querySelector('input[name="after_ftable"]')?.parentElement;
    const fSelect = document.createElement("select");
    fSelect.name = "after_ftable";
    fSelect.className = "form-select form-select-sm";
    fSelect.innerHTML = `<option value="">선택</option>${options}`;
    fTableCell.innerHTML = "";
    fTableCell.appendChild(fSelect);

    // 생보 select
    const lTableCell = row.querySelector('input[name="after_ltable"]')?.parentElement;
    const lSelect = document.createElement("select");
    lSelect.name = "after_ltable";
    lSelect.className = "form-select form-select-sm";
    lSelect.innerHTML = `<option value="">선택</option>${options}`;
    lTableCell.innerHTML = "";
    lTableCell.appendChild(lSelect);

    fSelect.addEventListener("change", e => {
      const selected = tables.find(
        t => t.table === e.target.value || t.table_name === e.target.value
      );
      if (selected) {
        row.querySelector('input[name="after_frate"]').value = selected.rate || "";
      }
    });

    lSelect.addEventListener("change", e => {
      const selected = tables.find(
        t => t.table === e.target.value || t.table_name === e.target.value
      );
      if (selected) {
        row.querySelector('input[name="after_lrate"]').value = selected.rate || "";
      }
    });

  } catch (err) {
    console.error("❌ 테이블 목록 로드 실패:", err);
  }
}
