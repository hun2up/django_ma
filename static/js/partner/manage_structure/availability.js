// static/js/partner/manage_structure/availability.js
import { els } from "./dom_refs.js";

export function checkInputAvailability() {
  const inputSection = els.inputSection;
  if (!inputSection) return;

  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;

  const selectedYear = parseInt(els.year.value, 10);
  const selectedMonth = parseInt(els.month.value, 10);
  const deadlineDay = parseInt(window.ManageStructureBoot?.deadlineDay || 10, 10);

  inputSection.removeAttribute("hidden");

  let disabled = false;
  if (selectedYear < currentYear || (selectedYear === currentYear && selectedMonth < currentMonth)) {
    disabled = true;
  } else if (selectedYear === currentYear && selectedMonth === currentMonth && today.getDate() > deadlineDay) {
    disabled = true;
  }

  inputSection.querySelectorAll("input, select, button").forEach((el) => {
    // 입력 섹션 내의 '검색' 버튼은 항상 동작해야 하면 아래 조건을 커스터마이징하세요.
    el.disabled = disabled;
  });

  if (disabled) inputSection.classList.add("disabled-mode");
  else inputSection.classList.remove("disabled-mode");
}
