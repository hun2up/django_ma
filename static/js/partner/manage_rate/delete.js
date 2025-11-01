// django_ma/static/js/partner/manage_rate/delete.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, getCSRFToken, alertBox } from "./utils.js";
import { fetchData } from "./fetch.js";

export function attachDeleteHandlers() {
  document.removeEventListener("click", handleDeleteClick);
  document.addEventListener("click", handleDeleteClick);
}

async function handleDeleteClick(e) {
  const btn = e.target.closest(".btnDeleteRow");
  if (!btn) return;

  // sub_admin 막기 (편제변경이랑 맞춤)
  const grade = els.root?.dataset?.userGrade;
  if (grade === "sub_admin") {
    alertBox("삭제 권한이 없습니다.");
    return;
  }

  const id = btn.dataset.id;
  if (!id) return;

  if (!confirm("해당 데이터를 삭제하시겠습니까?")) return;

  showLoading("삭제 중...");

  try {
    const res = await fetch(els.root.dataset.dataDeleteUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ id }),
    });

    const data = await res.json();
    if (data.status !== "success") {
      alertBox(data.message || "삭제에 실패했습니다.");
      return;
    }

    // 삭제 후 다시 조회 (현재 선택값 기준)
    const yearVal = els.yearSelect ? els.yearSelect.value : els.root.dataset.selectedYear;
    const monthVal = els.monthSelect ? els.monthSelect.value : els.root.dataset.selectedMonth;
    const ym = `${yearVal}-${monthVal.toString().padStart(2, "0")}`;
    const branch =
      (els.branchSelect && els.branchSelect.value) ||
      els.root.dataset.defaultBranch ||
      "";

    await fetchData({
      ym,
      branch,
      grade: els.root.dataset.userGrade,
    });
  } catch (err) {
    console.error(err);
    alertBox("삭제 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
