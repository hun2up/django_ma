// static/js/partner/manage_structure/delete.js
import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";

import * as Utils from "./utils.js";
const { alertBox, showLoading, hideLoading, getCSRFToken } = Utils;

export function attachDeleteHandlers() {
  document.querySelectorAll(".btnDeleteRow").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("이 항목을 삭제하시겠습니까?")) return;

      showLoading("삭제 중...");
      try {
        const res = await fetch(els.root.dataset.dataDeleteUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify({ id: btn.dataset.id }),
        });

        const data = await res.json();
        alertBox(data.message || "삭제 완료");

        if (data.status === "success") {
          await fetchData();
        }
      } catch (err) {
        console.error("❌ 삭제 중 오류:", err);
        alertBox("삭제 중 오류 발생");
      } finally {
        hideLoading();
      }
    });
  });
}
