// django_ma/static/js/common/part_branch_selector.js
(function () {
  "use strict";

  /* =========================================================
   * Part/Branch/Channel Selector Loader (Final Refactor)
   * ---------------------------------------------------------
   * - Backward compatible with legacy 2-step (part -> branch)
   * - Supports new 3-step (channel -> part -> branch) when
   *   #channelSelect exists on the page.
   * - Provides global window.loadPartsAndBranches(root) for manage_boot.js
   * - Robust against BFCache/pageshow persisted + duplicate binding
   * - Uses dataset URLs when provided; falls back to default endpoints
   ========================================================= */

  const ROOT_IDS = [
    "manage-structure",
    "manage-rate",
    "manage-table",
    "manage-efficiency",
    "manage-grades",
  ];

  const $ = (id) => document.getElementById(id);

  /* ----------------------------
   * Utils
   * ---------------------------- */
  function str(v) {
    return String(v ?? "").trim();
  }

  function findRootById(ids) {
    for (const id of ids) {
      const el = $(id);
      if (el) return el;
    }
    return null;
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

  function buildUrl(base, params) {
    const url = new URL(base, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      const val = str(v);
      if (!val) return;
      url.searchParams.set(k, val);
    });
    return url.toString();
  }

  async function fetchJson(url) {
    const res = await fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      // non-json response (login redirect/html)
    }
    if (!res.ok) {
      const msg = data?.message || data?.error || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    if (!data) throw new Error("Non-JSON response");
    return data;
  }

  function setOptions(selectEl, opts, placeholder) {
    if (!selectEl) return;
    const list = Array.isArray(opts) ? opts.map(str).filter(Boolean) : [];
    selectEl.innerHTML =
      `<option value="">${placeholder || "선택"}</option>` +
      list.map((v) => `<option value="${v}">${v}</option>`).join("");
  }

  function setLoading(selectEl, msg) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">${msg || "불러오는 중..."}</option>`;
    selectEl.disabled = true;
  }

  function setEmpty(selectEl, msg) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">${msg || "없음"}</option>`;
    selectEl.disabled = false;
  }

  function setError(selectEl, msg) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">${msg || "로드 실패"}</option>`;
    selectEl.disabled = false;
  }

  function setBtnEnabledByBranch(branchSelect, btnSearch) {
    if (!btnSearch) return;
    btnSearch.disabled = !str(branchSelect?.value);
  }

  function getEndpoints(root) {
    const d = root?.dataset || {};
    // dataset이 있으면 우선 사용, 없으면 fallback
    return {
      fetchChannelsUrl: str(d.fetchChannelsUrl) || "/partner/ajax/fetch-channels/",
      fetchPartsUrl: str(d.fetchPartsUrl) || "/partner/ajax/fetch-parts/",
      fetchBranchesUrl: str(d.fetchBranchesUrl) || "/partner/ajax/fetch-branches/",
    };
  }

  function hasChannelMode() {
    return !!$("channelSelect");
  }

  /* =========================================================
   * Loaders
   ========================================================= */
  async function loadChannels(root) {
    const channelSelect = $("channelSelect");
    if (!channelSelect) return [];

    const { fetchChannelsUrl } = getEndpoints(root);
    setLoading(channelSelect, "불러오는 중...");

    try {
      const data = await fetchJson(fetchChannelsUrl);
      const channels = Array.isArray(data.channels) ? data.channels : [];
      if (!channels.length) {
        setEmpty(channelSelect, "부문 없음");
        return [];
      }
      setOptions(channelSelect, channels, "부문 선택");
      channelSelect.disabled = false;
      return channels;
    } catch (e) {
      console.error("❌ [part_branch_selector] 부문 로드 실패:", e);
      setError(channelSelect, "부문 로드 실패");
      return [];
    }
  }

  async function loadParts(root, channel) {
    const partSelect = $("partSelect");
    if (!partSelect) return [];

    const { fetchPartsUrl } = getEndpoints(root);

    // channel 모드면 channel 없을 때 안내
    if (hasChannelMode()) {
      const ch = str(channel);
      if (!ch) {
        setEmpty(partSelect, "부문을 먼저 선택하세요");
        partSelect.disabled = true;
        return [];
      }
    }

    setLoading(partSelect, "불러오는 중...");

    try {
      const url = hasChannelMode()
        ? buildUrl(fetchPartsUrl, { channel: str(channel) })
        : fetchPartsUrl;

      const data = await fetchJson(url);
      const parts = Array.isArray(data.parts) ? data.parts : [];

      if (!parts.length) {
        setEmpty(partSelect, "부서 없음");
        return [];
      }

      setOptions(partSelect, parts, "부서 선택");
      partSelect.disabled = false;
      return parts;
    } catch (e) {
      console.error("❌ [part_branch_selector] 부서 로드 실패:", e);
      setError(partSelect, "부서 로드 실패");
      return [];
    }
  }

  async function loadBranches(root, part, channel) {
    const branchSelect = $("branchSelect");
    if (!branchSelect) return [];

    const { fetchBranchesUrl } = getEndpoints(root);

    const p = str(part);
    if (!p) {
      setEmpty(branchSelect, "부서를 먼저 선택하세요");
      branchSelect.disabled = true;
      return [];
    }

    setLoading(branchSelect, "불러오는 중...");

    try {
      const url = hasChannelMode()
        ? buildUrl(fetchBranchesUrl, { part: p, channel: str(channel) })
        : buildUrl(fetchBranchesUrl, { part: p });

      const data = await fetchJson(url);
      const branches = Array.isArray(data.branches) ? data.branches : [];

      if (!branches.length) {
        setEmpty(branchSelect, "지점 없음");
        return [];
      }

      setOptions(branchSelect, branches, "지점 선택");
      branchSelect.disabled = false;
      return branches;
    } catch (e) {
      console.error("❌ [part_branch_selector] 지점 로드 실패:", e);
      setError(branchSelect, "지점 로드 실패");
      return [];
    }
  }

  /* =========================================================
   * Main init / bind
   ========================================================= */
  async function initSelectors(root) {
    const grade = getGradeFromRoot(root);
    if (grade !== "superuser") return;

    const channelSelect = $("channelSelect");
    const partSelect = $("partSelect");
    const branchSelect = $("branchSelect");
    const btnSearch = getBtnSearch();

    if (!partSelect || !branchSelect) return;

    // BFCache/중복 바인딩 방지
    if (root.dataset.partBranchBound === "1") {
      // 이전에 "불러오는 중..."에서 멈춘 경우만 보정 시도
      if (hasChannelMode() && channelSelect) {
        const first = channelSelect.options?.[0]?.textContent || "";
        if (!channelSelect.options.length || first.includes("불러오는 중")) {
          await loadChannels(root);
        }
      } else {
        const first = partSelect.options?.[0]?.textContent || "";
        if (!partSelect.options.length || first.includes("불러오는 중")) {
          await loadParts(root, "");
        }
      }
      return;
    }
    root.dataset.partBranchBound = "1";

    if (btnSearch) btnSearch.disabled = true;

    /* ----------------------------
     * Initial values (hidden -> URL)
     * ---------------------------- */
    const initChannel = getInitValueFromHidden("selectedChannelInit") || getUrlParam("channel");
    const initPart = getInitValueFromHidden("selectedPartInit") || getUrlParam("part");
    const initBranch = getInitValueFromHidden("selectedBranchInit") || getUrlParam("branch");

    /* =========================================================
     * Mode A) 3-step: channel -> part -> branch
     ========================================================= */
    if (hasChannelMode() && channelSelect) {
      // 초기 UI
      setLoading(channelSelect, "불러오는 중...");
      setEmpty(partSelect, "부문을 먼저 선택하세요");
      partSelect.disabled = true;
      setEmpty(branchSelect, "부서를 먼저 선택하세요");
      branchSelect.disabled = true;

      // 1) 채널 로드
      await loadChannels(root);

      // 2) 초기값 적용: channel -> part -> branch
      if (initChannel) {
        channelSelect.value = initChannel;

        await loadParts(root, initChannel);

        if (initPart) {
          partSelect.value = initPart;

          await loadBranches(root, initPart, initChannel);

          if (initBranch) {
            branchSelect.value = initBranch;
            setBtnEnabledByBranch(branchSelect, btnSearch);
          }
        }
      }

      // 3) change bindings
      channelSelect.addEventListener("change", async () => {
        if (btnSearch) btnSearch.disabled = true;

        const ch = str(channelSelect.value);

        // reset dependent selects
        setEmpty(partSelect, ch ? "불러오는 중..." : "부문을 먼저 선택하세요");
        partSelect.disabled = true;

        setEmpty(branchSelect, "부서를 먼저 선택하세요");
        branchSelect.disabled = true;

        if (!ch) return;

        await loadParts(root, ch);
      });

      partSelect.addEventListener("change", async () => {
        if (btnSearch) btnSearch.disabled = true;

        const ch = str(channelSelect.value);
        const p = str(partSelect.value);

        await loadBranches(root, p, ch);
      });

      branchSelect.addEventListener("change", () => {
        setBtnEnabledByBranch(branchSelect, btnSearch);
      });

      return;
    }

    /* =========================================================
     * Mode B) legacy 2-step: part -> branch
     ========================================================= */
    setLoading(partSelect, "불러오는 중...");
    setEmpty(branchSelect, "부서를 먼저 선택하세요");
    branchSelect.disabled = true;

    // 1) parts 로드
    await loadParts(root, "");

    // 2) 초기값 복원
    if (initPart) {
      partSelect.value = initPart;
      await loadBranches(root, initPart, "");

      if (initBranch) {
        branchSelect.value = initBranch;
        setBtnEnabledByBranch(branchSelect, btnSearch);
      }
    }

    // 3) change bindings
    partSelect.addEventListener("change", async () => {
      if (btnSearch) btnSearch.disabled = true;
      await loadBranches(root, partSelect.value, "");
    });

    branchSelect.addEventListener("change", () => {
      setBtnEnabledByBranch(branchSelect, btnSearch);
    });
  }

  /* =========================================================
   * Global API for manage_boot.js compatibility
   ========================================================= */
  window.loadPartsAndBranches = async function (rootIdOrEl) {
    const root = typeof rootIdOrEl === "string" ? $(rootIdOrEl) : rootIdOrEl;
    if (!root) return;
    await initSelectors(root);
  };

  /* =========================================================
   * Auto init
   ========================================================= */
  function autoInit() {
    const root = findRootById(ROOT_IDS);
    if (!root) return;
    window.loadPartsAndBranches(root).catch((e) => console.error(e));
  }

  document.addEventListener("DOMContentLoaded", autoInit);
  window.addEventListener("pageshow", (e) => {
    if (e.persisted) autoInit();
  });
})();
