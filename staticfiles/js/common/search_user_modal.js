/**
 * django_ma/static/js/common/search_user_modal.js (FINAL - READY STATE SAFE)
 * -------------------------------------------------------------------------
 * 공통 대상자 검색 모달
 * - DOMContentLoaded 타이밍 이슈(늦게 로드) 방지: readyState 기반 즉시 init
 * - root(dataset) 우선으로 search URL 결정: data-search-user-url
 * - /api/accounts/search-user/ 가 404면 자동 fallback URL로 재시도
 * - 결과 클릭 시:
 *    1) activeRow(또는 fallback row)에 대상자 필드 자동입력
 *    2) tg_display가 있으면 "성명(사번)" 형태로 동기화
 *    3) userSelected 이벤트(document/window) 발행
 * - 동적 행 대응(active row tracking)
 * -------------------------------------------------------------------------
 */

(() => {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[search_user_modal]", ...a);

  /** @type {HTMLTableRowElement|null} */
  let activeRow = null;

  /* =======================================================
   * Utils
   * ======================================================= */
  const toStr = (v) => String(v ?? "").trim();

  function escapeHtml(v) {
    const s = String(v ?? "");
    return s
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function tryHideModal(modalEl) {
    try {
      const inst = window.bootstrap?.Modal?.getInstance?.(modalEl);
      if (inst) inst.hide();
    } catch (_) {}
  }

  async function safeReadJson(res) {
    const text = await res.text().catch(() => "");
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      return { _raw: text.slice(0, 300) };
    }
  }

  /* =======================================================
   * Root / Scope
   * ======================================================= */
  function getActiveRoot() {
    return (
      document.getElementById("manage-structure") ||
      document.getElementById("manage-rate") ||
      document.getElementById("manage-efficiency") ||
      document.getElementById("manage-calculate") ||
      document.getElementById("manage-table") ||
      document.getElementById("deposit-home") ||
      document.getElementById("support-form") ||
      null
    );
  }

  function getUserGrade(root) {
    return toStr(root?.dataset?.userGrade || window.currentUser?.grade || "");
  }

  function getPageScope(root) {
    const id = root?.id || "";
    if (
      id === "manage-structure" ||
      id === "manage-rate" ||
      id === "manage-efficiency" ||
      id === "manage-calculate" ||
      id === "support-form"
    ) {
      return "branch";
    }
    return "default";
  }

  function findBranchSelectEl(root) {
    const selectors = [
      "#branchSelect",
      "#branch",
      "#id_branch",
      "[data-branch-select]",
      'select[name="branch"]',
      'select[name="branchSelect"]',
    ];

    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) return el;
    }

    const inRoot = root?.querySelector?.('select[id*="branch"], select[name*="branch"]');
    if (inRoot) return inRoot;

    return null;
  }

  function getEffectiveBranchForSearch(root) {
    const grade = getUserGrade(root);
    const sel = findBranchSelectEl(root);

    const selectedBranch = toStr(sel?.value || "");
    const uBranch = toStr(window.currentUser?.branch || "");
    const dsBranch = toStr(root?.dataset?.defaultBranch || "");

    if (grade === "superuser") return selectedBranch || uBranch || dsBranch;
    return uBranch || dsBranch || selectedBranch;
  }

  /* =======================================================
   * Active row tracking
   * ======================================================= */
  function clearActiveMarks(root) {
    const scopeRoot = root || document;
    try {
      scopeRoot
        .querySelectorAll("tr.input-row.active, tr.input-row.active-input-row")
        .forEach((x) => {
          x.classList.remove("active");
          x.classList.remove("active-input-row");
        });
    } catch (_) {}
  }

  function markActiveRowFromBtn(btn) {
    const tr = btn?.closest?.("tr.input-row") || btn?.closest?.("tr");
    if (!tr) return;

    const root = getActiveRoot();
    clearActiveMarks(root);

    try {
      tr.classList.add("active-input-row");
      if (tr.classList.contains("input-row")) tr.classList.add("active");
    } catch (_) {}

    activeRow = tr;
    log("activeRow set", tr);
  }

  function getFallbackRow(root) {
    const inputTable = root?.querySelector?.("#inputTable");
    const rows = inputTable?.querySelectorAll?.("tr.input-row");
    if (rows && rows.length) return rows[rows.length - 1];
    return null;
  }

  function resolveTargetRow(root) {
    if (activeRow && document.contains(activeRow)) return activeRow;

    const r1 = root?.querySelector?.("tr.input-row.active");
    if (r1) return r1;

    const r2 = root?.querySelector?.("tr.input-row.active-input-row");
    if (r2) return r2;

    const a1 = document.querySelector("tr.input-row.active");
    if (a1) return a1;

    const a2 = document.querySelector("tr.input-row.active-input-row");
    if (a2) return a2;

    return getFallbackRow(root);
  }

  /* =======================================================
   * Field helpers (robust)
   * ======================================================= */
  function findField(row, key) {
    if (!row || !key) return null;

    let el =
      row.querySelector?.(`[name="${key}"]`) ||
      row.querySelector?.(`[name="${key}[]"]`) ||
      null;
    if (el) return el;

    el = row.querySelector?.(`[data-field="${key}"]`) || null;
    if (el) return el;

    el = row.querySelector?.(`.${key}`) || null;
    if (el) return el;

    el = row.querySelector?.(`[id^="${key}"]`) || null;
    if (el) return el;

    return null;
  }

  function setValueIfExists(row, key, value) {
    const el = findField(row, key);
    if (!el) return false;

    el.value = value ?? "";
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function syncDisplayIfExists(row, displaySelector, name, id) {
    const disp = row?.querySelector?.(displaySelector);
    if (!disp) return false;

    const n = toStr(name);
    const i = toStr(id);
    disp.value = n && i ? `${n}(${i})` : (n || i || "");
    disp.dispatchEvent(new Event("input", { bubbles: true }));
    disp.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function autofillSelectedUser(row, selected) {
    if (!row) return;

    const name = toStr(selected?.name || "");
    const id = toStr(selected?.id || "");
    const branch = toStr(selected?.branch || "");
    const rank = toStr(selected?.rank || "");
    const part = toStr(selected?.part || "");

    const teamLabel = [selected?.team_a, selected?.team_b, selected?.team_c]
      .map(toStr)
      .filter(Boolean)
      .join(" ");

    // ✅ hidden 필드 채우기
    setValueIfExists(row, "tg_name", name) || setValueIfExists(row, "target_name", name);
    setValueIfExists(row, "tg_id", id) || setValueIfExists(row, "target_id", id);
    setValueIfExists(row, "tg_branch", teamLabel || "-") || setValueIfExists(row, "target_branch", teamLabel || "-");
    setValueIfExists(row, "tg_rank", rank) || setValueIfExists(row, "rank", rank);
    setValueIfExists(row, "tg_part", part) || setValueIfExists(row, "target_part", part);

    // ✅ 표시용(대상자) "성명(사번)"
    syncDisplayIfExists(row, ".tg_display", name, id) ||
      syncDisplayIfExists(row, ".target_display", name, id);
  }

  /* =======================================================
   * URL Resolver + 404 fallback fetch
   * ======================================================= */
  function resolveSearchUrls(modalEl, root) {
    const modalUrl = toStr(modalEl?.dataset?.searchUrl || "");
    const rootUrl = toStr(root?.dataset?.searchUserUrl || "");
    const fallbacks = ["/board/search-user/", "/api/accounts/search-user/"];

    const urls = [modalUrl, rootUrl, ...fallbacks].map(toStr).filter(Boolean);
    return Array.from(new Set(urls));
  }

  async function fetchSearch(urls, params) {
    let lastErr = null;

    for (const base of urls) {
      try {
        const u = new URL(base, window.location.origin);

        if (params.q) {
          u.searchParams.set("q", params.q);
          u.searchParams.set("keyword", params.q);
        }
        if (params.scope) u.searchParams.set("scope", params.scope);
        if (params.branch) u.searchParams.set("branch", params.branch);

        const res = await fetch(u.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (res.status === 404) {
          log("404 fallback next", u.toString());
          continue;
        }

        const data = await safeReadJson(res);

        if (!res.ok) throw new Error(data?.message || `HTTP ${res.status}`);

        return { ok: true, url: u.toString(), data };
      } catch (e) {
        lastErr = e;
        log("fetch failed", base, e);
      }
    }

    return { ok: false, error: lastErr || new Error("검색 API 호출 실패(모든 후보 URL 실패)") };
  }

  function normalizeUserList(data) {
    if (!data) return [];
    if (Array.isArray(data.results)) return data.results;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.users)) return data.users;
    return [];
  }

  /* =======================================================
   * Render
   * ======================================================= */
  function renderLoading(resultsBox) {
    resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;
  }
  function renderEmpty(resultsBox) {
    resultsBox.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
  }
  function renderError(resultsBox) {
    resultsBox.innerHTML = `<div class="text-center text-danger py-3">검색 실패</div>`;
  }
  function renderResults(resultsBox, list) {
    resultsBox.innerHTML = list
      .map((u0) => {
        const u = u0 || {};
        const name = escapeHtml(u.name || "");
        const id = escapeHtml(u.id || "");
        const branchV = escapeHtml(u.branch || "");
        const regist = escapeHtml(u.regist || "");
        const enter = escapeHtml(u.enter || "-");
        const quit = escapeHtml(u.quit || "재직중");

        return `
          <button type="button"
            class="list-group-item list-group-item-action search-result"
            data-id="${escapeHtml(u.id)}"
            data-name="${escapeHtml(u.name)}"
            data-branch="${escapeHtml(u.branch || "")}"
            data-rank="${escapeHtml(u.rank || "")}"
            data-part="${escapeHtml(u.part || "")}"
            data-team-a="${escapeHtml(u.team_a || "")}"
            data-team-b="${escapeHtml(u.team_b || "")}"
            data-team-c="${escapeHtml(u.team_c || "")}"
            data-regist="${escapeHtml(u.regist || "")}"
            data-enter="${escapeHtml(u.enter || "")}"
            data-quit="${escapeHtml(u.quit || "재직중")}">
            <div class="d-flex justify-content-between">
              <span><strong>${name}</strong> (${id}) ${regist ? `(${regist})` : ""}</span>
              <small class="text-muted">${branchV}</small>
            </div>
            <small class="text-muted">입사일: ${enter} / 퇴사일: ${quit}</small>
          </button>
        `;
      })
      .join("");
  }

  /* =======================================================
   * Init
   * ======================================================= */
  function init() {
    const modalEl = document.getElementById("searchUserModal");
    if (!modalEl) return;

    if (modalEl.dataset.bound === "true") return;
    modalEl.dataset.bound = "true";

    const form = modalEl.querySelector("#searchUserForm");
    const input = modalEl.querySelector("#searchKeyword");
    const resultsBox = modalEl.querySelector("#searchResults");

    if (!form || !resultsBox) {
      console.warn("[search_user_modal] form/resultsBox not found");
      return;
    }

    // ✅ btnOpenSearch 클릭 → activeRow 세팅 (capture=true)
    document.addEventListener(
      "click",
      (e) => {
        const btn = e.target?.closest?.(".btnOpenSearch");
        if (!btn) return;
        markActiveRowFromBtn(btn);
      },
      true
    );

    // ✅ 검색 submit
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const keyword = toStr(input?.value || "");
      if (!keyword) return window.alert("검색어를 입력하세요.");

      const root = getActiveRoot();
      const scope = getPageScope(root);
      const grade = getUserGrade(root);

      let branch = "";
      if (scope === "branch") {
        if (!root) return window.alert("페이지 루트를 찾을 수 없습니다.");
        branch = getEffectiveBranchForSearch(root);

        if (grade === "superuser" && !branch) {
          return window.alert("지점 정보가 없습니다. (부서/지점을 먼저 선택해주세요)");
        }
      }

      renderLoading(resultsBox);

      const urls = resolveSearchUrls(modalEl, root);
      const params = {
        q: keyword,
        scope: scope === "branch" ? "branch" : "",
        branch: scope === "branch" && grade === "superuser" ? branch : "",
      };

      try {
        const r = await fetchSearch(urls, params);
        if (!r.ok) throw r.error;

        const list = normalizeUserList(r.data);
        if (!list.length) return renderEmpty(resultsBox);

        renderResults(resultsBox, list);
        log("search ok", { used: r.url, count: list.length, scope, grade });
      } catch (err) {
        console.error("❌ 검색 오류:", err);
        renderError(resultsBox);
      }
    });

    // ✅ 결과 클릭
    resultsBox.addEventListener("click", (e) => {
      const item = e.target?.closest?.(".search-result");
      if (!item) return;

      const selected = {
        id: toStr(item.dataset.id),
        name: toStr(item.dataset.name),
        branch: toStr(item.dataset.branch),
        rank: toStr(item.dataset.rank),
        part: toStr(item.dataset.part),
        team_a: toStr(item.dataset.teamA),
        team_b: toStr(item.dataset.teamB),
        team_c: toStr(item.dataset.teamC),
        regist: toStr(item.dataset.regist),
        enter: toStr(item.dataset.enter),
        quit: toStr(item.dataset.quit),
      };

      const root = getActiveRoot();
      const row = resolveTargetRow(root);

      if (!row) {
        console.warn("[search_user_modal] target row not found");
      } else {
        autofillSelectedUser(row, selected);
      }

      const ev = new CustomEvent("userSelected", { detail: selected });
      document.dispatchEvent(ev);
      window.dispatchEvent(ev);

      tryHideModal(modalEl);

      if (input) input.value = "";
      resultsBox.innerHTML = "";
    });

    // ✅ 모달 닫힐 때 초기화
    modalEl.addEventListener("hidden.bs.modal", () => {
      if (input) input.value = "";
      resultsBox.innerHTML = "";
    });

    log("bound ok");
  }

  // ✅ 핵심: DOMContentLoaded 이전/이후 로드 모두 대응
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
