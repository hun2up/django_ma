// django_ma/static/js/common/part_branch_selector.js

/**
 * ✅ 공용 부서/지점 선택기 (superuser 전용)
 * - 편제변경 / 요율변경 / 테이블관리 페이지 공용
 * - main_admin/sub_admin은 자동조회 흐름이라 보통 실행하지 않음
 */
document.addEventListener("DOMContentLoaded", async () => {
  // ✅ 세 페이지 중 하나라도 있으면 실행
  const root =
    document.getElementById("manage-structure") ||
    document.getElementById("manage-rate") ||
    document.getElementById("manage-table");
  if (!root) return;

  const userGrade = root.dataset.userGrade;
  if (userGrade !== "superuser") return;

  const partSelect = document.getElementById("partSelect");
  const branchSelect = document.getElementById("branchSelect");

  // 페이지별 검색 버튼 id가 다를 수 있어 후보 탐색
  const btnSearch =
    document.getElementById("btnSearch") ||
    document.getElementById("btnSearchPeriod");

  if (!partSelect || !branchSelect) return;

  /* =======================================================
     📘 부서 목록 불러오기
  ======================================================= */
  try {
    partSelect.innerHTML = `<option>불러오는 중...</option>`;
    const res = await fetch("/partner/ajax/fetch-parts/");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.parts && data.parts.length > 0) {
      partSelect.innerHTML =
        `<option value="">부서 선택</option>` +
        data.parts.map((p) => `<option value="${p}">${p}</option>`).join("");
    } else {
      partSelect.innerHTML = `<option value="">부서 없음</option>`;
    }

    console.log("✅ [part_branch_selector] 부서 목록 로드 완료");
  } catch (err) {
    console.error("❌ [part_branch_selector] 부서 목록 로드 오류:", err);
    partSelect.innerHTML = `<option value="">로드 실패</option>`;
  }

  /* =======================================================
     📘 부서 선택 → 지점 목록 불러오기
  ======================================================= */
  partSelect.addEventListener("change", async () => {
    const part = partSelect.value;
    branchSelect.innerHTML = `<option>불러오는 중...</option>`;
    branchSelect.disabled = true;
    if (btnSearch) btnSearch.disabled = true;

    if (!part) return;

    try {
      const res2 = await fetch(
        `/partner/ajax/fetch-branches/?part=${encodeURIComponent(part)}`
      );
      if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
      const data2 = await res2.json();

      if (data2.branches && data2.branches.length > 0) {
        branchSelect.innerHTML =
          `<option value="">지점 선택</option>` +
          data2.branches.map((b) => `<option value="${b}">${b}</option>`).join("");
      } else {
        branchSelect.innerHTML = `<option value="">지점 없음</option>`;
      }

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
  branchSelect.addEventListener("change", () => {
    if (btnSearch) btnSearch.disabled = !branchSelect.value;
    if (branchSelect.value) {
      console.log(`🔹 [part_branch_selector] 지점 선택됨: ${branchSelect.value}`);
    }
  });
});
