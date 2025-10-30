/**
 * =======================================================
 * 📌 Superuser용 부서/지점 선택 로직 (공용 스크립트)
 * -------------------------------------------------------
 * - 공통적으로 사용하는 부서/지점 드롭다운 제어
 * - Ajax로 DB에서 part / branch 목록을 불러옴
 * - 각 페이지의 root element에 data-user-grade 속성이 있어야 함
 * 
 * 사용 방법:
 * 1. HTML에 다음 요소들이 존재해야 함:
 *    - select#partSelect
 *    - select#branchSelect
 *    - data-user-grade="superuser" 속성 (루트 컨테이너)
 * 
 * 2. 필요한 경우 `window.loadPartsAndBranches()`를 호출해 초기화 가능
 * =======================================================
 */

window.loadPartsAndBranches = async function(rootElementId = null) {
  const root = rootElementId
    ? document.getElementById(rootElementId)
    : document.querySelector("[data-user-grade]");

  if (!root) return;

  const userGrade = root.dataset.userGrade;
  const fetchPartsUrl = "/partner/ajax/fetch-parts/";
  const fetchBranchesUrl = "/partner/ajax/fetch-branches/";

  const partSelect = document.getElementById("partSelect");
  const branchSelect = document.getElementById("branchSelect");

  if (userGrade !== "superuser" || !partSelect || !branchSelect) return;

  /** -------------------------------
   * ✅ 부서 목록 불러오기
   * ------------------------------- */
  async function loadParts() {
    try {
      const res = await fetch(fetchPartsUrl, { credentials: 'same-origin' });
      const data = await res.json();
      partSelect.innerHTML = `<option value="">선택</option>`;
      data.parts.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        partSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("부서 목록 불러오기 실패:", err);
      partSelect.innerHTML = `<option value="">불러오기 실패</option>`;
    }
  }

  /** -------------------------------
   * ✅ 선택된 부서의 지점 목록 불러오기
   * ------------------------------- */
  async function loadBranches(part) {
    try {
      const res = await fetch(`${fetchBranchesUrl}?part=${encodeURIComponent(part)}`, { credentials: 'same-origin' });
      const data = await res.json();
      branchSelect.innerHTML = `<option value="">지점을 선택하세요</option>`;
      data.branches.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        branchSelect.appendChild(opt);
      });
      branchSelect.disabled = false;
    } catch (err) {
      console.error("지점 목록 불러오기 실패:", err);
      branchSelect.innerHTML = `<option value="">불러오기 실패</option>`;
      branchSelect.disabled = true;
    }
  }

  /** -------------------------------
   * ✅ 이벤트 핸들링
   * ------------------------------- */
  partSelect.addEventListener("change", () => {
    const part = partSelect.value;
    branchSelect.innerHTML = `<option value="">불러오는 중...</option>`;
    branchSelect.disabled = true;
    if (part) loadBranches(part);
  });

  // ✅ 초기 부서 목록 로드
  await loadParts();
};
