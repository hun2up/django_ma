// django_ma/static/js/partner/manage_structure/delete.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";

export function attachDeleteHandlers() {
  document.removeEventListener("click", handleDeleteClick); // 중복방지
  document.addEventListener("click", handleDeleteClick);
}

async function handleDeleteClick(e) {
  const btn = e.target.closest(".btnDeleteRow");
  if (!btn) return;

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
    if (data.status === "success") {
      alertBox("삭제 완료!");
      // ✅ 삭제 후 데이터 갱신
      const ym = `${els.year.value}-${String(els.month.value).padStart(2, "0")}`;
      const branch = els.branch?.value || window.currentUser?.branch || "";
      await fetchData(ym, branch);
    } else {
      alertBox(data.message || "삭제 실패");
    }
  } catch (err) {
    console.error("❌ 삭제 오류:", err);
    alertBox("삭제 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
