/**
 * django_ma/static/js/common/search_user_modal.js (FINAL REFACTOR)
 * -----------------------------------------------------
 * 공통 대상자 검색 모달
 * - /api/accounts/search-user/ 기반
 * - manage-structure / manage-rate / manage-efficiency / manage-calculate 는 scope=branch 사용
 * - 결과 클릭 시 userSelected 이벤트 document + window 모두 발행
 * - resultsBox에만 클릭 위임
 *
 * ✅ 주요 보강
 * - scope/root는 submit 시점에 재판정 (DOM 늦게 로드/부분 갱신 대응)
 * - branchSelect 후보를 다중 탐색 (템플릿 id 변형 대응)
 * - superuser만 branch 파라미터 전송 (백엔드 정책과 일치)
 * - 활성행 탐색을 root 내부 우선으로 (다른 테이블 오탐 방지)
 * -----------------------------------------------------
 */

(() => {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[search_user_modal]", ...a);

  let activeRow = null;

  /* -----------------------------
   * helpers
   * ----------------------------- */
  function toStr(v) {
    return String(v ?? "").trim();
  }

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

  function getPageScope(root) {
    const id = root?.id || "";
    if (
      id === "manage-efficiency" ||
      id === "manage-calculate" ||
      id === "support-form"
    ) {
      return "branch";
    }
    return "default";
  }

  function getUserGrade(root) {
    return toStr(root?.dataset?.userGrade || window.currentUser?.grade || "");
  }

  function findBranchSelectEl(root) {
    // superuser 지점 선택 셀렉트는 페이지마다 id가 다를 수 있어서 후보를 넓게 잡음
    // 우선순위: 명시적인 셀렉터 -> 흔한 id -> root 내부 -> document
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

    // root 안에 branch 관련 select가 있는 경우(안전 fallback)
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

    // ✅ superuser는 선택지점 우선
    if (grade === "superuser") return selectedBranch || uBranch || dsBranch;

    // ✅ 그 외는 본인지점 우선(서버도 그렇게 처리)
    return uBranch || dsBranch || selectedBranch;
  }

  function safeEscapeHtml(v) {
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

  /* -----------------------------
   * active row tracking
   * ----------------------------- */
  function clearActiveMarks(root) {
    try {
      const scopeRoot = root || document;
      scopeRoot
        .querySelectorAll("tr.input-row.active, tr.input-row.active-input-row")
        .forEach((x) => {
          x.classList.remove("active");
          x.classList.remove("active-input-row");
        });
    } catch (_) {}
  }

  function markActiveRowFromBtn(btn) {
    const tr = btn?.closest?.("tr");
    if (!tr) return;

    const root = getActiveRoot();
    clearActiveMarks(root);

    // ✅ 둘 다 부여해서 구조/요율/효율 어디서든 잡히게
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
    // 1) 저장된 activeRow
    if (activeRow && document.contains(activeRow)) return activeRow;

    // 2) root 내부에서 우선 탐색(오탐 방지)
    const r1 = root?.querySelector?.("tr.input-row.active");
    if (r1) return r1;

    const r2 = root?.querySelector?.("tr.input-row.active-input-row");
    if (r2) return r2;

    // 3) document fallback
    const a1 = document.querySelector("tr.input-row.active");
    if (a1) return a1;

    const a2 = document.querySelector("tr.input-row.active-input-row");
    if (a2) return a2;

    // 4) 마지막 행
    return getFallbackRow(root);
  }

  /* -----------------------------
   * robust field finder
   * ----------------------------- */
  function findField(row, key) {
    if (!row || !key) return null;

    // 1) name
    let el =
      row.querySelector?.(`[name="${key}"]`) ||
      row.querySelector?.(`[name="${key}[]"]`) ||
      null;
    if (el) return el;

    // 2) data-field
    el = row.querySelector?.(`[data-field="${key}"]`) || null;
    if (el) return el;

    // 3) class
    el = row.querySelector?.(`.${key}`) || null;
    if (el) return el;

    // 4) id startswith (tg_name_0 같은 케이스)
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

  function autofillSelectedUser(row, selected) {
    if (!row) return;

    const name = toStr(selected?.name || "");
    const id = toStr(selected?.id || "");
    const branch = toStr(selected?.branch || "");
    const rank = toStr(selected?.rank || "");
    const part = toStr(selected?.part || "");

    // ✅ 대상자 필드(편제/요율 공통) - 존재하는 것만 채움
    setValueIfExists(row, "tg_name", name) || setValueIfExists(row, "target_name", name);
    setValueIfExists(row, "tg_id", id) || setValueIfExists(row, "target_id", id);
    setValueIfExists(row, "tg_branch", branch) || setValueIfExists(row, "target_branch", branch);
    setValueIfExists(row, "tg_rank", rank) || setValueIfExists(row, "rank", rank);

    // optional
    setValueIfExists(row, "tg_part", part) || setValueIfExists(row, "target_part", part);
  }

  /* -----------------------------
   * init
   * ----------------------------- */
  function init() {
    const modalEl = document.getElementById("searchUserModal");
    if (!modalEl) return;

    // 모달 기준 1회 바인딩
    if (modalEl.dataset.bound === "true") return;
    modalEl.dataset.bound = "true";

    const form = modalEl.querySelector("#searchUserForm");
    const input = modalEl.querySelector("#searchKeyword");
    const resultsBox = modalEl.querySelector("#searchResults");

    const searchUrl = toStr(modalEl.dataset.searchUrl || "/api/accounts/search-user/");

    if (!form || !resultsBox) {
      console.warn("[search_user_modal] form/resultsBox not found");
      return;
    }

    // ✅ btnOpenSearch 클릭 → activeRow 세팅 (capture=true)
    // (동적 생성 행도 잡히도록 document 위임)
    document.addEventListener(
      "click",
      (e) => {
        const btn = e.target?.closest?.(".btnOpenSearch");
        if (!btn) return;
        markActiveRowFromBtn(btn);
      },
      true
    );

    // 🔍 검색
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const keyword = toStr(input?.value || "");
      if (!keyword) return window.alert("검색어를 입력하세요.");

      // ✅ submit 시점에 root/scope 재판정
      const root = getActiveRoot();
      const scope = getPageScope(root);
      const grade = getUserGrade(root);

      let branch = "";
      if (scope === "branch") {
        if (!root) return window.alert("페이지 루트를 찾을 수 없습니다.");

        branch = getEffectiveBranchForSearch(root);

        // superuser는 branch 선택이 필수(선택지점/본인지점/기본지점 중 하나라도 있어야 함)
        if (grade === "superuser" && !branch) {
          return window.alert("지점 정보가 없습니다. (부서/지점을 먼저 선택해주세요)");
        }
      }

      resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

      try {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set("q", keyword);

        if (scope === "branch") {
          url.searchParams.set("scope", "branch");
          if (grade === "superuser") url.searchParams.set("branch", branch);
        }

        const res = await fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json().catch(() => ({}));
        const list = Array.isArray(data?.results) ? data.results : Array.isArray(data?.items) ? data.items : [];

        if (!list.length) {
          resultsBox.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
          return;
        }

        resultsBox.innerHTML = list
          .map((u0) => {
            const u = u0 || {};
            const name = safeEscapeHtml(u.name || "");
            const id = safeEscapeHtml(u.id || "");
            const branchV = safeEscapeHtml(u.branch || "");
            const regist = safeEscapeHtml(u.regist || "");
            const enter = safeEscapeHtml(u.enter || "-");
            const quit = safeEscapeHtml(u.quit || "재직중");

            return `
              <button type="button"
                class="list-group-item list-group-item-action search-result"
                data-id="${safeEscapeHtml(u.id)}"
                data-name="${safeEscapeHtml(u.name)}"
                data-branch="${safeEscapeHtml(u.branch || "")}"
                data-rank="${safeEscapeHtml(u.rank || "")}"
                data-part="${safeEscapeHtml(u.part || "")}"
                data-regist="${safeEscapeHtml(u.regist || "")}"
                data-enter="${safeEscapeHtml(u.enter || "")}"
                data-quit="${safeEscapeHtml(u.quit || "재직중")}">
                <div class="d-flex justify-content-between">
                  <span><strong>${name}</strong> (${id}) ${regist ? `(${regist})` : ""}</span>
                  <small class="text-muted">${branchV}</small>
                </div>
                <small class="text-muted">입사일: ${enter} / 퇴사일: ${quit}</small>
              </button>
            `;
          })
          .join("");

        log("search ok", { scope, grade, count: list.length });
      } catch (err) {
        console.error("❌ 검색 오류:", err);
        resultsBox.innerHTML = `<div class="text-center text-danger py-3">검색 실패</div>`;
      }
    });

    // ✅ 결과 클릭(위임은 resultsBox에만)
    resultsBox.addEventListener("click", (e) => {
      const item = e.target?.closest?.(".search-result");
      if (!item) return;

      const selected = {
        id: toStr(item.dataset.id),
        name: toStr(item.dataset.name),
        branch: toStr(item.dataset.branch),
        rank: toStr(item.dataset.rank),
        part: toStr(item.dataset.part),
        regist: toStr(item.dataset.regist),
        enter: toStr(item.dataset.enter),
        quit: toStr(item.dataset.quit),
      };

      const root = getActiveRoot();
      const row = resolveTargetRow(root);

      if (row) autofillSelectedUser(row, selected);

      // ✅ 기존 이벤트 기반 처리 로직 유지(요율/편제 input_rows.js 등)
      const ev = new CustomEvent("userSelected", { detail: selected });
      document.dispatchEvent(ev);
      window.dispatchEvent(ev);

      tryHideModal(document.getElementById("searchUserModal"));

      // reset input/results
      if (input) input.value = "";
      resultsBox.innerHTML = "";
    });

    // 모달 닫힐 때 초기화
    modalEl.addEventListener("hidden.bs.modal", () => {
      if (input) input.value = "";
      resultsBox.innerHTML = "";
      // activeRow는 유지 (여러 번 검색 시 편함)
      // 필요 시 아래 주석 해제:
      // activeRow = null;
    });

    log("bound ok", { searchUrl });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
