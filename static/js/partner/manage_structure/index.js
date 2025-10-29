// static/js/partner/manage_structure/index.js
import { els, initSelectOptions } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { saveRows } from "./save.js";
import { resetInputSection, initInputRowEvents } from "./input_rows.js";
import { attachDeleteHandlers } from "./delete.js";
import { setupDeadlineButton } from "./deadline.js";
import { checkInputAvailability } from "./availability.js";
import { showLoading, hideLoading } from "./utils.js";
import "./modal_search.js"; // 내부에서 이벤트 바인딩 수행

document.addEventListener("DOMContentLoaded", async () => {
  if (!els.root) return;

  // superuser 부서/지점 선택 초기화 (공용 스크립트 필요)
  if (window.currentUser?.grade === "superuser" && window.loadPartsAndBranches) {
    await window.loadPartsAndBranches("manage-structure");
  }

  // 기본 select 옵션
  initSelectOptions();

  // DataTable
  if (window.jQuery && $.fn.DataTable) {
    $(els.mainTable).DataTable({
      language: { search: "검색 :", lengthMenu: "표시 _MENU_ 개" },
      order: [],
    });
  }

  // 이벤트 연결
  els.btnSearch?.addEventListener("click", () => fetchData());
  els.btnSaveRows?.addEventListener("click", saveRows);
  els.btnResetRows?.addEventListener("click", resetInputSection);
  initInputRowEvents();
  attachDeleteHandlers();
  setupDeadlineButton();

  // 권한별 초기 조회
  const g = window.currentUser?.grade;
  if (["main_admin", "sub_admin"].includes(g)) {
    const ym = `${els.year.value}-${els.month.value}`;
    setTimeout(() => fetchData(ym, window.currentUser?.branch || ""), 300);
  }

  // 입력 가능 여부
  checkInputAvailability();

  // (선택) 디버깅/가시화를 위해 입력 섹션 기본 오픈
  els.inputSection?.removeAttribute("hidden");
});
