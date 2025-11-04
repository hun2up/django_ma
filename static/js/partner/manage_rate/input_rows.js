// django_ma/static/js/partner/manage_rate/input_rows.js

// ======================================================
// 📘 요율변경 요청 페이지 - 입력행 관리 (v5.2)
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";

/* =======================================================
   📘 초기화
   ======================================================= */
export function initInputRowEvents() {
  // ✅ 행 추가
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

    // ✅ 요청자 정보 자동 입력
    fillRequesterInfo(newRow);
    allowEditableFields(newRow);

    tbody.appendChild(newRow);

    // ✅ 새 행 활성화
    tbody.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    newRow.classList.add("active");
  });

  // ✅ 초기화 버튼
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // ✅ 행 삭제 (이벤트 위임)
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

  // ✅ 행 클릭 시 active 처리
  document.addEventListener("click", (e) => {
    const tr = e.target.closest(".input-row");
    if (!tr) return;
    els.inputTable.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    tr.classList.add("active");
  });

  // ✅ 첫 행 초기 설정
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => (el.readOnly = true));
    fillRequesterInfo(firstRow);
    allowEditableFields(firstRow);
    firstRow.classList.add("active");
  }

  // ✅ 모달에서 사용자 선택 이벤트
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
}

/* =======================================================
   ✅ 전체 초기화
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
   ✅ 수정 가능한 칸만 활성화
   ======================================================= */
function allowEditableFields(row) {
  ["after_ftable", "after_ltable", "memo"].forEach((name) => {
    const el = row.querySelector(`input[name="${name}"]`);
    if (el) el.readOnly = false;
  });
}

/* =======================================================
   ✅ 대상자 상세정보 불러오기
   ======================================================= */
async function fetchTargetDetail(targetId) {
  const url = `/partner/ajax/rate-user-detail/?user_id=${encodeURIComponent(targetId)}`;
  const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
  return res.json();
}

/* =======================================================
   ✅ 대상자 선택 시 자동입력 + 테이블 드롭다운
   ======================================================= */
export async function fillTargetInfo(row, targetId) {
  try {
    const data = await fetchTargetDetail(targetId);
    if (data.status !== "success") {
      alertBox(data.message || "대상자 정보를 불러오지 못했습니다.");
      return;
    }

    const info = data.data || {};

    // ✅ 요청자 정보 자동입력 (비어있을 때만)
    const rqName = row.querySelector('input[name="rq_name"]');
    const rqId = row.querySelector('input[name="rq_id"]');
    if (!rqName?.value) rqName.value = window.currentUser?.name || "";
    if (!rqId?.value) rqId.value = window.currentUser?.id || "";

    // ✅ 대상자 정보 채우기
    row.querySelector('input[name="tg_name"]').value = info.target_name || "";
    row.querySelector('input[name="tg_id"]').value = info.target_id || "";
    row.querySelector('input[name="before_ftable"]').value = info.non_life_table || "";
    row.querySelector('input[name="before_frate"]').value = info.non_life_rate || "";
    row.querySelector('input[name="before_ltable"]').value = info.life_table || "";
    row.querySelector('input[name="before_lrate"]').value = info.life_rate || "";

    await loadTableDropdowns(row);
  } catch (err) {
    console.error("❌ 대상자 정보 로드 실패:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}


/* =======================================================
   ✅ 요청자 branch 기준 테이블 목록 드롭다운
   ======================================================= */
async function loadTableDropdowns(row) {
  const branch = window.currentUser?.branch || "";
  if (!branch) return;

  try {
    const res = await fetch(`/partner/ajax_table_fetch/?branch=${encodeURIComponent(branch)}`);
    const data = await res.json();
    const tables = data.rows || [];

    const options = tables
      .map((t) => `<option value="${t.table || t.table_name}">${t.table || t.table_name}</option>`)
      .join("");

    // 손보
    const fParent = row.querySelector('input[name="after_ftable"]')?.parentElement;
    if (fParent) {
      const fSelect = document.createElement("select");
      fSelect.name = "after_ftable";
      fSelect.className = "form-select form-select-sm";
      fSelect.innerHTML = `<option value="">선택</option>${options}`;
      fParent.innerHTML = "";
      fParent.appendChild(fSelect);

      fSelect.addEventListener("change", (e) => {
        const selected = tables.find(
          (t) => t.table === e.target.value || t.table_name === e.target.value
        );
        if (selected) {
          row.querySelector('input[name="after_frate"]').value = selected.rate || "";
        }
      });
    }

    // 생보
    const lParent = row.querySelector('input[name="after_ltable"]')?.parentElement;
    if (lParent) {
      const lSelect = document.createElement("select");
      lSelect.name = "after_ltable";
      lSelect.className = "form-select form-select-sm";
      lSelect.innerHTML = `<option value="">선택</option>${options}`;
      lParent.innerHTML = "";
      lParent.appendChild(lSelect);

      lSelect.addEventListener("change", (e) => {
        const selected = tables.find(
          (t) => t.table === e.target.value || t.table_name === e.target.value
        );
        if (selected) {
          row.querySelector('input[name="after_lrate"]').value = selected.rate || "";
        }
      });
    }
  } catch (err) {
    console.error("❌ 테이블 목록 로드 실패:", err);
  }
}
