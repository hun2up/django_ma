// django_ma/static/js/partner/manage_rate/delete.js
// ======================================================
// 📘 요율변경 요청 페이지 - 삭제 로직 (dataset 키 통일 버전)
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, getCSRFToken, alertBox, selectedYM } from "./utils.js";
import { fetchData } from "./fetch.js";

/* ==========================
   ✅ 공통: grade/branch/ym
========================== */
function getGrade() {
  return (els.root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") return (els.branchSelect?.value || "").trim();
  return (window.currentUser?.branch || els.root?.dataset?.defaultBranch || "").trim();
}

function buildFetchPayload() {
  const ym = selectedYM(els.yearSelect, els.monthSelect);
  return {
    ym,
    branch: getEffectiveBranch(),
    grade: getGrade(),
    level: (els.root?.dataset?.userLevel || "").trim(),
    team_a: (els.root?.dataset?.teamA || "").trim(),
    team_b: (els.root?.dataset?.teamB || "").trim(),
    team_c: (els.root?.dataset?.teamC || "").trim(),
  };
}

/* ============================================================
   ✅ 삭제 이벤트 등록 (중복 방지)
============================================================ */
export function attachDeleteHandlers() {
  document.removeEventListener("click", handleDeleteClick);
  document.addEventListener("click", handleDeleteClick);
}

/* ============================================================
   ✅ 삭제 처리
============================================================ */
async function handleDeleteClick(e) {
  const btn = e.target.closest(".btnDeleteRow");
  if (!btn || !els.root) return;

  const grade = getGrade();
  if (grade === "sub_admin") {
    alertBox("삭제 권한이 없습니다. (SUB_ADMIN)");
    return;
  }

  const id = (btn.dataset.id || "").trim();
  if (!id) return;

  if (!confirm("해당 데이터를 삭제하시겠습니까?")) return;

  const deleteUrl = (els.root.dataset.deleteUrl || "").trim(); // ✅ dataset 키 통일
  if (!deleteUrl) {
    alertBox("삭제 URL이 설정되어 있지 않습니다. (data-delete-url 확인)");
    return;
  }

  showLoading("삭제 중...");

  try {
    const res = await fetch(deleteUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ id }),
    });

    const data = await res.json();

    if (!res.ok || data.status !== "success") {
      throw new Error(data.message || `삭제 실패 (HTTP ${res.status})`);
    }

    alertBox("삭제가 완료되었습니다.");

    // ✅ 삭제 후 재조회
    await fetchData(buildFetchPayload());
  } catch (err) {
    console.error("❌ [rate/delete] 오류:", err);
    alertBox("삭제 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
