// django_ma/static/js/partner/manage_structure/delete.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";

/**
 * ✅ 삭제 버튼 이벤트 바인딩
 * - 중복 리스너 방지
 * - 클릭 시 handleDeleteClick 실행
 */
export function attachDeleteHandlers() {
  document.removeEventListener("click", handleDeleteClick); // 중복방지
  document.addEventListener("click", handleDeleteClick);
}

/**
 * ✅ 삭제 처리 (안전형)
 */
async function handleDeleteClick(e) {
  const btn = e.target.closest(".btnDeleteRow");
  if (!btn) return;

  const id = btn.dataset.id;
  if (!id) return;

  if (!confirm("해당 데이터를 삭제하시겠습니까?")) return;

  // 중복 클릭 방지
  btn.disabled = true;
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

    const text = await res.text();
    console.log("📦 [delete] Raw Response:", text);

    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    let data = {};
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("서버 응답 파싱 실패");
    }

    if (data.status === "success") {
      alertBox("✅ 삭제 완료!");

      // ✅ 삭제 후 재조회 (안전 실행)
      try {
        const ym = `${els.year.value}-${String(els.month.value).padStart(2, "0")}`;
        const branch = els.branch?.value || window.currentUser?.branch || "";
        await fetchData(ym, branch);
      } catch (refErr) {
        console.warn("⚠️ 삭제 후 재조회 중 오류:", refErr);
        alertBox("삭제는 완료되었지만, 테이블 새로고침 중 오류가 발생했습니다.");
      }
    } else {
      alertBox(data.message || "삭제 실패");
    }
  } catch (err) {
    console.error("❌ 삭제 오류:", err);
    alertBox("삭제 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
    btn.disabled = false; // ✅ 버튼 재활성화
  }
}
