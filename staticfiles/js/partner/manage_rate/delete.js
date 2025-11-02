// django_ma/static/js/partner/manage_rate/delete.js
import { els } from "./dom_refs.js";
import { showLoading, hideLoading, getCSRFToken, alertBox } from "./utils.js";
import { fetchData } from "./fetch.js";

/* ============================================================
   ✅ 삭제 이벤트 등록 (중복 방지)
============================================================ */
export function attachDeleteHandlers() {
  document.removeEventListener("click", handleDeleteClick);
  document.addEventListener("click", handleDeleteClick);
}

/* ============================================================
   ✅ 삭제 처리 함수
============================================================ */
async function handleDeleteClick(e) {
  const btn = e.target.closest(".btnDeleteRow");
  if (!btn) return;

  // 🔹 등급 체크 (sub_admin은 삭제 불가)
  const grade = els.root?.dataset?.userGrade || "";
  if (grade === "sub_admin") {
    alertBox("삭제 권한이 없습니다. (SUB_ADMIN)");
    return;
  }

  const id = btn.dataset.id;
  if (!id) {
    console.warn("[rate/delete] ❌ 버튼에 data-id 누락");
    return;
  }

  // 🔹 사용자 확인
  if (!confirm("해당 데이터를 삭제하시겠습니까?")) return;

  showLoading("삭제 중...");

  try {
    // 🔹 요청 URL 검증
    const deleteUrl = els.root?.dataset?.dataDeleteUrl;
    if (!deleteUrl) {
      alertBox("삭제 URL이 설정되어 있지 않습니다.");
      return;
    }

    // 🔹 서버 요청
    const res = await fetch(deleteUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ id }),
    });

    // 🔹 응답 파싱
    if (!res.ok) {
      console.error(`[rate/delete] 서버 응답 오류: ${res.status}`);
      alertBox(`삭제 요청 실패 (코드 ${res.status})`);
      return;
    }

    const data = await res.json();

    if (data.status !== "success") {
      alertBox(data.message || "삭제에 실패했습니다.");
      console.warn("[rate/delete] 실패 응답:", data);
      return;
    }

    console.log(`✅ [rate/delete] ID=${id} 삭제 완료`);

    // =====================================================
    // ✅ 삭제 후 재조회
    // =====================================================
    const yearVal =
      els.yearSelect?.value || els.root.dataset.selectedYear || new Date().getFullYear();
    const monthVal =
      els.monthSelect?.value || els.root.dataset.selectedMonth || new Date().getMonth() + 1;
    const ym = `${yearVal}-${monthVal.toString().padStart(2, "0")}`;
    const branch =
      (els.branchSelect && els.branchSelect.value) ||
      els.root.dataset.defaultBranch ||
      "";

    await fetchData({
      ym,
      branch,
      grade,
      level: els.root.dataset.userLevel || "",
      team_a: els.root.dataset.teamA || "",
      team_b: els.root.dataset.teamB || "",
      team_c: els.root.dataset.teamC || "",
    });

    alertBox("삭제가 완료되었습니다.");
  } catch (err) {
    console.error("❌ [rate/delete] 예외 발생:", err);
    alertBox("삭제 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
