// django_ma/static/js/partner/manage_rate/index.js
import { initInputRowEvents } from "./input_rows.js";
import { els, initDOMRefs } from "./dom_refs.js";
import { initManageBoot } from "../../common/manage_boot.js";

initManageBoot("rate"); // ✅ 공통 부트 호출 (fetchData 자동 실행 포함)

document.addEventListener("DOMContentLoaded", () => {
  initDOMRefs();

  // 1️⃣ 연도/월도 초기화
  const now = new Date();
  const yearSel = els.year;
  const monthSel = els.month;
  if (yearSel && monthSel) {
    yearSel.innerHTML = "";
    for (let y = now.getFullYear() - 2; y <= now.getFullYear() + 1; y++) {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = `${y}년`;
      if (y === now.getFullYear()) opt.selected = true;
      yearSel.appendChild(opt);
    }

    monthSel.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = `${m}월`;
      if (m === now.getMonth() + 1) opt.selected = true;
      monthSel.appendChild(opt);
    }
  }

  // 2️⃣ 요청자 자동입력 및 행 제어
  if (els.inputTable) initInputRowEvents();

  // 3️⃣ 검색 버튼 이벤트 (수동 조회용)
  els.btnSearch?.addEventListener("click", () => {
    const year = els.year.value;
    const month = els.month.value;
    const ym = `${year}-${String(month).padStart(2, "0")}`;
    const branch = els.branch?.value?.trim() || window.currentUser?.branch || "";

    console.log("🔍 수동 조회 실행", { ym, branch });
    els.inputSection?.removeAttribute("hidden");
    els.mainTable?.removeAttribute("hidden");

    import("./fetch.js").then(({ fetchData }) => {
      fetchData(ym, branch, window.currentUser);
    });
  });
});
