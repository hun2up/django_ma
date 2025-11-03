// django_ma/static/js/parnter/manage_rate/input_rows.js

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

  // 삭제
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

  // 행 클릭 시 active 표시
  document.addEventListener("click", (e) => {
    const tr = e.target.closest(".input-row");
    if (!tr) return;
    els.inputTable.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    tr.classList.add("active");
  });

  // 첫 행 초기 세팅
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => (el.readOnly = true));
    fillRequesterInfo(firstRow);
    allowEditableFields(firstRow);
    firstRow.classList.add("active");
  }
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
======================================================= */
function allowEditableFields(row) {
  ["after_ftable", "after_ltable", "memo"].forEach((name) => {
    const el = row.querySelector(`input[name="${name}"]`);
    if (el) el.readOnly = false;
  });
}
