// django_ma/static/js/common/part_branch_selector.js
(function () {
  const ROOT_IDS = ["manage-structure", "manage-rate", "manage-table", "manage-efficiency", "manage-grades"];

  const $ = (id) => document.getElementById(id);

  function findRootById(ids) {
    for (const id of ids) {
      const el = $(id);
      if (el) return el;
    }
    return null;
  }

  function str(v) {
    return String(v ?? "").trim();
  }

  function getGradeFromRoot(root) {
    return str(root?.dataset?.userGrade);
  }

  function getBtnSearch() {
    // 페이지마다 검색 버튼 id가 다름
    return $("btnSearchPeriod") || $("btnSearch");
  }

  function getUrlParam(name) {
    try {
      const url = new URL(window.location.href);
      return str(url.searchParams.get(name));
    } catch {
      return "";
    }
  }

  function getInitValueFromHidden(id) {
    return str($(id)?.value);
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
        `<option value="">부서 선택</option>` + parts.map((p) => `<option value="${p}">${p}</option>`).join("");

      if (!parts.length) partSelect.innerHTML = `<option value="">부서 없음</option>`;

      partSelect.disabled = false;
      return parts;
    } catch (e) {
      console.error("❌ [part_branch_selector] 부서 로드 실패:", e);
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

    const p = str(part);
    if (!p) {
      branchSelect.innerHTML = `<option value="">부서를 먼저 선택하세요</option>`;
      return [];
    }

    try {
      const data = await fetchJson(`/partner/ajax/fetch-branches/?part=${encodeURIComponent(p)}`);
      const branches = Array.isArray(data.branches) ? data.branches : [];

      branchSelect.innerHTML =
        `<option value="">지점 선택</option>` + branches.map((b) => `<option value="${b}">${b}</option>`).join("");

      if (!branches.length) branchSelect.innerHTML = `<option value="">지점 없음</option>`;

      branchSelect.disabled = false;
      return branches;
    } catch (e) {
      console.error("❌ [part_branch_selector] 지점 로드 실패:", e);
      branchSelect.innerHTML = `<option value="">로드 실패</option>`;
      branchSelect.disabled = false;
      return [];
    }
  }

  function setBtnEnabledByBranch(branchSelect, btnSearch) {
    if (!btnSearch) return;
    btnSearch.disabled = !str(branchSelect?.value);
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

    // 중복 바인딩 방지
    if (root.dataset.partBranchBound === "1") {
      // 혹시 parts가 아직 로딩중이면 한 번 더 시도
      if (!partSelect.options.length || partSelect.options[0]?.textContent?.includes("불러오는 중")) {
        await loadParts();
      }
      return;
    }
    root.dataset.partBranchBound = "1";

    if (btnSearch) btnSearch.disabled = true;

    // 1) parts 로드
    await loadParts();

    // 2) 초기값 복원: hidden -> URL
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

    // 3) change 이벤트
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
