// django_ma/static/js/common/part_branch_selector.js
/**
 * ✅ 공용 부서/지점 선택기 (superuser 전용)
 * - 부서 선택 → 지점 목록 로드
 * - 지점 선택 시 검색 버튼 자동 활성화
 */
document.addEventListener("DOMContentLoaded", async () => {
  const root = document.getElementById("manage-table");
  if (!root) return;

  const userGrade = root.dataset.userGrade;
  if (userGrade !== "superuser") return; // main_admin은 자동조회라 실행 X

  const partSelect = document.getElementById("partSelect");
  const branchSelect = document.getElementById("branchSelect");
  const btnSearch = document.getElementById("btnSearch");

  /* =======================================================
     📘 부서 목록 불러오기
  ======================================================= */
  try {
    const res = await fetch("/partner/ajax/fetch-parts/");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    partSelect.innerHTML =
      `<option value="">부서 선택</option>` +
      data.parts.map((p) => `<option value="${p}">${p}</option>`).join("");

    console.log("✅ [part_branch_selector] 부서 목록 로드 완료");
  } catch (err) {
    console.error("❌ [part_branch_selector] 부서 목록 로드 오류:", err);
    partSelect.innerHTML = `<option value="">로드 실패</option>`;
  }

  /* =======================================================
     📘 부서 선택 → 지점 목록 불러오기
  ======================================================= */
  partSelect?.addEventListener("change", async () => {
    const part = partSelect.value;
    branchSelect.innerHTML = `<option>불러오는 중...</option>`;
    branchSelect.disabled = true;
    btnSearch.disabled = true;

    if (!part) return;

    try {
      const res2 = await fetch(`/partner/ajax/fetch-branches/?part=${encodeURIComponent(part)}`);
      if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
      const data2 = await res2.json();

      branchSelect.innerHTML =
        `<option value="">지점 선택</option>` +
        data2.branches.map((b) => `<option value="${b}">${b}</option>`).join("");

      branchSelect.disabled = false;
      console.log("✅ [part_branch_selector] 지점 목록 로드 완료");
    } catch (err) {
      console.error("❌ [part_branch_selector] 지점 로드 오류:", err);
      branchSelect.innerHTML = `<option value="">로드 실패</option>`;
    }
  });

  /* =======================================================
     📘 지점 선택 시 → 검색 버튼 활성화
  ======================================================= */
  branchSelect?.addEventListener("change", () => {
    btnSearch.disabled = !branchSelect.value;
    if (branchSelect.value) {
      console.log(`🔹 [part_branch_selector] 지점 선택됨: ${branchSelect.value}`);
    }
  });
});
