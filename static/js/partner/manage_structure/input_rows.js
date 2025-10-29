// static/js/partner/manage_structure/input_rows.js
import { els } from "./dom_refs.js";

export function initInputRowEvents() {
  // 추가
  els.btnAddRow?.addEventListener("click", () => {
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length >= 10) {
      alert("대상자는 한 번에 10명까지 입력 가능합니다.");
      return;
    }
    const newRow = rows[0].cloneNode(true);
    newRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
    });
    tbody.appendChild(newRow);
  });

  // 초기화
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // 삭제(동적 위임)
  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("btnRemoveRow")) return;
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length <= 1) {
      alert("행이 하나뿐이라 삭제할 수 없습니다.");
      return;
    }
    e.target.closest(".input-row").remove();
  });
}

export function resetInputSection() {
  const tbody = els.inputTable.querySelector("tbody");
  const rows = tbody.querySelectorAll(".input-row");

  rows.forEach((r, idx) => {
    if (idx > 0) r.remove();
  });

  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
    });
  }
}
