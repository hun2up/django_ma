// django_ma/static/js/partner/manage_structure/deadline.js

/*
import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { checkInputAvailability } from "./availability.js";

export function setupDeadlineButton() {
  els.btnDeadline?.addEventListener("click", async () => {
    const branch = els.branch?.value || "";
    const day = els.deadline?.value || "";

    if (!branch || !day) return alertBox("지점과 기한을 선택해주세요.");

    showLoading("기한 설정 중...");
    try {
      const res = await fetch(els.root.dataset.setDeadlineUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ branch, day }),
      });
      const data = await res.json();

      alertBox(data.message || "기한 설정 완료");
      if (data.status === "success") {
        window.ManageStructureBoot = window.ManageStructureBoot || {};
        window.ManageStructureBoot.deadlineDay = parseInt(day, 10);
        checkInputAvailability();
      }
    } catch (err) {
      console.error(err);
      alertBox("기한 설정 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  });
}
*/