// static/js/partner/manage_structure/index.js
console.log("🚀 index.js 진입:", import.meta.url);

document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ DOMContentLoaded");

  const yearEl = document.getElementById("yearSelect");
  const monthEl = document.getElementById("monthSelect");

  console.log("yearEl:", yearEl, "monthEl:", monthEl);

  if (!yearEl || !monthEl) {
    console.warn("⚠️ year/month 요소가 없음");
    return;
  }

  // 템플릿에서 내려준 부트 데이터
  const boot = window.ManageStructureBoot || {};
  const now = new Date();

  // 여기서 숫자로 강제
  const selectedYear = parseInt(boot.selectedYear || now.getFullYear(), 10);
  const selectedMonth = parseInt(boot.selectedMonth || now.getMonth() + 1, 10);

  // 연도 채우기
  yearEl.innerHTML = "";
  for (let y = 2023; y <= 2026; y++) {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = `${y}년`;
    if (y === selectedYear) opt.selected = true;
    yearEl.appendChild(opt);
  }

  // 월도 채우기
  monthEl.innerHTML = "";
  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = `${m}월`;
    if (m === selectedMonth) opt.selected = true;
    monthEl.appendChild(opt);
  }

  console.log(
    "✅ 드롭다운 생성 끝:",
    yearEl.value,
    monthEl.value,
    "(boot:", boot, ")"
  );
});
