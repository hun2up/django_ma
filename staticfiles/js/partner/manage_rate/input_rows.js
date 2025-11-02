// django_ma/static/js/partner/manage_rate/input_rows.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { fetchData } from "./fetch.js";

/* =======================================================
   📘 입력 행 관련 로직 (요율변경 요청 페이지)
   ======================================================= */
export function initInputRowEvents() {
  // ✅ 추가 버튼
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
      el.readOnly = true; // ✅ 기본적으로 전부 readonly
    });

    fillRequesterInfo(newRow); // 요청자 정보 자동 입력
    allowEditableFields(newRow); // 변경가능 칸만 해제
    tbody.appendChild(newRow);
  });

  // ✅ 초기화 버튼
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // ✅ 삭제 버튼 (동적 위임)
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

  // ✅ 페이지 최초 로드시 요청자 정보 입력
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => (el.readOnly = true));
    fillRequesterInfo(firstRow);
    allowEditableFields(firstRow);
  }
}

/* =======================================================
   ✅ 요청자 정보 자동입력 (branch 포함)
   ======================================================= */
function fillRequesterInfo(row) {
  const user = window.currentUser || {};
  row.querySelector('input[name="rq_name"]').value = user.name || "";
  row.querySelector('input[name="rq_id"]').value = user.id || "";
  // ✅ 요청자 소속 자동입력 (지점명만 활용)
  const branchInput = row.querySelector('input[name="rq_branch"]');
  if (branchInput) branchInput.value = user.branch || "";
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
  }
}

/* =======================================================
   ✅ 변경 가능 필드만 수정 허용
   ======================================================= */
function allowEditableFields(row) {
  const editableNames = ["non_life_table_after", "life_table_after", "memo"];
  editableNames.forEach((name) => {
    const el = row.querySelector(`input[name="${name}"]`);
    if (el) el.readOnly = false;
  });
}

/* =======================================================
   ✅ 대상자 선택 후 자동입력
   ======================================================= */
export async function fillTargetInfo(row, targetId) {
  try {
    const res = await fetch(`/partner/ajax_rate_user_detail/?user_id=${targetId}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await res.json();
    if (data.status !== "success") {
      alertBox(data.message || "대상자 정보를 불러오지 못했습니다.");
      return;
    }

    const info = data.data;
    const user = window.currentUser || {};

    // 요청자 정보 자동입력
    row.querySelector('input[name="rq_name"]').value = user.name || "";
    row.querySelector('input[name="rq_id"]').value = user.id || "";

    // 대상자 정보
    row.querySelector('input[name="tg_name"]').value = info.target_name || "";
    row.querySelector('input[name="tg_id"]').value = info.target_id || "";

    // ✅ 변경전 테이블명 및 요율 (테이블관리 페이지와 연동)
    row.querySelector('input[name="before_ftable"]').value = info.non_life_table || "";
    row.querySelector('input[name="before_frate"]').value = info.non_life_rate || "";
    row.querySelector('input[name="before_ltable"]').value = info.life_table || "";
    row.querySelector('input[name="before_lrate"]').value = info.life_rate || "";

    // 전체 필드 readonly 처리 후 변경후 칸만 수정 가능
    row.querySelectorAll("input").forEach((el) => (el.readOnly = true));
    allowEditableFields(row);
  } catch (err) {
    console.error("❌ 대상자 정보 로드 실패:", err);
    alertBox("대상자 정보를 불러오는 중 오류가 발생했습니다.");
  }
}


/* =======================================================
   ✅ 검색 모달에서 선택 시 자동 채움
   ======================================================= */
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

  // ✅ 모달 닫기
  const modalEl = document.getElementById("searchUserModal");
  if (modalEl) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  }
});
