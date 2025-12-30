// django_ma/static/js/common/part_branch_selector.js
(function () {
  const ROOT_IDS = [
    "manage-structure",
    "manage-rate",
    "manage-table",
    "manage-efficiency",
    "manage-grades",
  ];

  function findRootById(ids) {
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) return el;
    }
    return null;
  }

  const $ = (id) => document.getElementById(id);

  function getGradeFromRoot(root) {
    return String(root?.dataset?.userGrade || "").trim();
  }

  function getBtnSearch() {
    return $("btnSearchPeriod") || $("btnSearch");
  }

  function getUrlParam(name) {
    try {
      const url = new URL(window.location.href);
      return String(url.searchParams.get(name) || "").trim();
    } catch {
      return "";
    }
  }

  function getInitValueFromHidden(id) {
    const el = $(id);
    return String(el?.value || "").trim();
  }

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function loadParts() {
    const partSelect = $("partSelect");
    if (!partSelect) return [];

    partSelect.innerHTML = `<option value="">불러오는 중...</option>`;
    partSelect.disabled = true;

    try {
      const data = await fetchJson("/partner/ajax/fetch-parts/");
      const parts = Array.isArray(data.parts) ? data.parts : [];

      partSelect.innerHTML =
        `<option value="">부서 선택</option>` +
        parts.map((p) => `<option value="${p}">${p}</option>`).join("");

      if (!parts.length) partSelect.innerHTML = `<option value="">부서 없음</option>`;

      partSelect.disabled = false;
      console.log("✅ [part_branch_selector] 부서 목록 로드 완료", parts.length);
      return parts;
    } catch (e) {
      console.error("❌ [part_branch_selector] 부서 목록 로드 실패:", e);
      partSelect.innerHTML = `<option value="">로드 실패</option>`;
      partSelect.disabled = false;
      return [];
    }
  }

  async function loadBranches(part) {
    const branchSelect = $("branchSelect");
    if (!branchSelect) return [];

    branchSelect.innerHTML = `<option value="">불러오는 중...</option>`;
    branchSelect.disabled = true;

    const p = String(part || "").trim();
    if (!p) {
      branchSelect.innerHTML = `<option value="">부서를 먼저 선택하세요</option>`;
      return [];
    }

    try {
      const data = await fetchJson(`/partner/ajax/fetch-branches/?part=${encodeURIComponent(p)}`);
      const branches = Array.isArray(data.branches) ? data.branches : [];

      branchSelect.innerHTML =
        `<option value="">지점 선택</option>` +
        branches.map((b) => `<option value="${b}">${b}</option>`).join("");

      if (!branches.length) branchSelect.innerHTML = `<option value="">지점 없음</option>`;

      branchSelect.disabled = false;
      console.log("✅ [part_branch_selector] 지점 목록 로드 완료", branches.length);
      return branches;
    } catch (e) {
      console.error("❌ [part_branch_selector] 지점 목록 로드 실패:", e);
      branchSelect.innerHTML = `<option value="">로드 실패</option>`;
      branchSelect.disabled = false;
      return [];
    }
  }

  function setBtnEnabledByBranch(branchSelect, btnSearch) {
    if (!btnSearch) return;
    btnSearch.disabled = !String(branchSelect?.value || "").trim();
  }

  // ✅ manage_boot.js 호환 전역
  window.loadPartsAndBranches = async function (rootIdOrEl) {
    const root = typeof rootIdOrEl === "string" ? $(rootIdOrEl) : rootIdOrEl;
    if (!root) return;

    const grade = getGradeFromRoot(root);
    if (grade !== "superuser") return;

    const partSelect = $("partSelect");
    const branchSelect = $("branchSelect");
    const btnSearch = getBtnSearch();
    if (!partSelect || !branchSelect) return;

    // ✅ 중복 바인딩 방지
    if (root.dataset.partBranchBound === "1") {
      // 혹시 로드가 안 된 상태면 parts만이라도 로드
      if (!partSelect.options.length || partSelect.options[0]?.textContent?.includes("불러오는 중")) {
        await loadParts();
      }
      return;
    }
    root.dataset.partBranchBound = "1";

    if (btnSearch) btnSearch.disabled = true;

    // 1) parts 로드
    await loadParts();

    // 2) 초기값 복원 우선순위: hidden -> URL
    const initPart = getInitValueFromHidden("selectedPartInit") || getUrlParam("part");
    const initBranch = getInitValueFromHidden("selectedBranchInit") || getUrlParam("branch");

    if (initPart) {
      partSelect.value = initPart;
      await loadBranches(initPart);

      if (initBranch) {
        branchSelect.value = initBranch;
        setBtnEnabledByBranch(branchSelect, btnSearch);
      }
    }

    // 3) 이벤트
    partSelect.addEventListener("change", async () => {
      if (btnSearch) btnSearch.disabled = true;
      await loadBranches(partSelect.value);
    });

    branchSelect.addEventListener("change", () => {
      setBtnEnabledByBranch(branchSelect, btnSearch);
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    const root = findRootById(ROOT_IDS);
    if (!root) return;

    window.loadPartsAndBranches(root).catch((e) => console.error(e));
  });
})();
