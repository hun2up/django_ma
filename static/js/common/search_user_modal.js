/**
 * django_ma/static/js/common/search_user_modal.js  (REFRACTOR - STRUCTURE FIX)
 * -----------------------------------------------------
 * 공통 대상자 검색 모달
 * - /api/accounts/search-user/ 기반
 * - manage-structure / manage-rate 에서만 scope=branch 전송
 * - deposit-home도 root로 인식
 * - 결과 클릭 시 userSelected 이벤트 document + window 모두 발행
 * - resultsBox에만 클릭 위임
 *
 * ✅ FIX(편제변경 반영 불가 이슈)
 * - btnOpenSearch 클릭 시 활성 입력행을 "active" + "active-input-row" 둘 다로 표시
 *   (편제변경 input_rows.js는 보통 .input-row.active 를 기준으로 찾음)
 * - 선택 시 activeRow가 없더라도:
 *   1) .input-row.active 우선
 *   2) .input-row.active-input-row 다음
 *   3) 마지막 input-row fallback
 * - 입력 필드 탐색을 name 외에 data-field / class / id(tg_*)까지 확장(있을 때만)
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
      document.getElementById("manage-table") ||
      document.getElementById("deposit-home") ||
      null
    );
  }

  function getPageScope(root) {
    const id = root?.id || "";
    if (id === "manage-structure" || id === "manage-rate") return "branch";
    return "default";
  }

  function getEffectiveBranchForSearch(root) {
    const grade = toStr(root?.dataset?.userGrade || window.currentUser?.grade || "");
    const sel = document.getElementById("branchSelect");
    const selectedBranch = toStr(sel?.value || "");

    const uBranch = toStr(window.currentUser?.branch || "");
    const dsBranch = toStr(root?.dataset?.defaultBranch || "");

    if (grade === "superuser") return selectedBranch || uBranch || dsBranch;
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
   * active row tracking (핵심 FIX)
   * - 편제변경: .input-row.active 를 찾는 경우가 많음
   * ----------------------------- */
  function clearActiveMarks() {
    try {
      document.querySelectorAll("tr.input-row.active, tr.input-row.active-input-row").forEach((x) => {
        x.classList.remove("active");
        x.classList.remove("active-input-row");
      });
    } catch (_) {}
  }

  function markActiveRowFromBtn(btn) {
    const tr = btn?.closest?.("tr");
    if (!tr) return;

    clearActiveMarks();

    // ✅ 둘 다 부여해서 구조/요율 어디서든 잡히게
    try {
      tr.classList.add("active-input-row");
      if (tr.classList.contains("input-row")) tr.classList.add("active");
    } catch (_) {}

    activeRow = tr;
    log("activeRow set", tr);
  }

  function getFallbackRow() {
    const root = getActiveRoot();
    const inputTable = root?.querySelector?.("#inputTable");
    const rows = inputTable?.querySelectorAll?.("tr.input-row");
    if (rows && rows.length) return rows[rows.length - 1];
    return null;
  }

  function resolveTargetRow() {
    // 1) search 버튼 클릭으로 저장된 activeRow
    if (activeRow && document.contains(activeRow)) return activeRow;

    // 2) 편제/요율 input_rows.js가 붙인 .active
    const a1 = document.querySelector("tr.input-row.active");
    if (a1) return a1;

    // 3) 우리쪽 .active-input-row
    const a2 = document.querySelector("tr.input-row.active-input-row");
    if (a2) return a2;

    // 4) 마지막 행
    return getFallbackRow();
  }

  /* -----------------------------
   * robust field finder (안전)
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

    if (modalEl.dataset.bound === "true") return;
    modalEl.dataset.bound = "true";

    const root = getActiveRoot();
    const scope = getPageScope(root);

    const form = modalEl.querySelector("#searchUserForm");
    const input = modalEl.querySelector("#searchKeyword");
    const resultsBox = modalEl.querySelector("#searchResults");

    const searchUrl = toStr(modalEl.dataset.searchUrl || "/api/accounts/search-user/");

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

    // 🔍 검색
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const keyword = toStr(input?.value || "");
      if (!keyword) return window.alert("검색어를 입력하세요.");

      let branch = "";
      if (scope === "branch") {
        if (!root) return window.alert("페이지 루트를 찾을 수 없습니다.");
        branch = getEffectiveBranchForSearch(root);
        if (!branch) {
          return window.alert("지점 정보가 없습니다. (부서/지점을 먼저 선택하거나 로그인 사용자 지점 확인)");
        }
      }

      resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

      try {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set("q", keyword);

        if (scope === "branch") {
          url.searchParams.set("scope", "branch");
          url.searchParams.set("branch", branch);
        }

        const res = await fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json().catch(() => ({}));
        const list = Array.isArray(data?.results) ? data.results : [];

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
                  <span><strong>${name}</strong> (${id}) (${regist || "-"})</span>
                  <small class="text-muted">${branchV}</small>
                </div>
                <small class="text-muted">입사일: ${enter} / 퇴사일: ${quit}</small>
              </button>
            `;
          })
          .join("");
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

      // ✅ (핵심) 편제변경/요율변경 모두에서 “활성행”을 확실히 잡아 자동 채움
      const row = resolveTargetRow();
      if (row) autofillSelectedUser(row, selected);

      // ✅ 기존 이벤트 기반 처리 로직 유지(요율/편제 input_rows.js 등)
      const ev = new CustomEvent("userSelected", { detail: selected });
      document.dispatchEvent(ev);
      window.dispatchEvent(ev);

      tryHideModal(item.closest?.("#searchUserModal") || document.getElementById("searchUserModal"));

      const modalEl = document.getElementById("searchUserModal");
      const input = modalEl?.querySelector?.("#searchKeyword");
      if (input) input.value = "";
      resultsBox.innerHTML = "";
    });

    // 모달 닫힐 때 초기화
    modalEl.addEventListener("hidden.bs.modal", () => {
      if (input) input.value = "";
      resultsBox.innerHTML = "";
      // activeRow는 유지해도 되지만, 구조쪽에서 오작동하면 아래 주석 해제 가능
      // activeRow = null;
    });

    log("bound ok", { scope, searchUrl });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
