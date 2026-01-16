/* django_ma/static/js/commission/deposit_home.js
 * Deposit Home (채권현황) - FINAL (Refactor)
 *
 * ✅ 핵심 동작 (기존 유지)
 * - 대상자 선택(userSelected 이벤트) → pushState로 URL만 변경 + 즉시 fetch&render (새로고침 없음)
 * - 뒤로가기(popstate) → URL의 user 파라미터로 재렌더
 * - data-bind 기반 자동 바인딩(템플릿 legacy 키 ↔ API 키 mismatch는 alias로 흡수)
 * - surety/other 테이블 렌더 + 말줄임(.ellipsis-cell) 클릭 시 전체보기 모달
 * - 지원신청서 버튼: user 선택 시 활성화 → support-pdf URL로 이동
 */

(() => {
  "use strict";

  /* ==========================================================
   * 0) Boot / Guard
   * ========================================================== */
  const root = document.getElementById("deposit-home");
  if (!root) return;

  const DEBUG = false;
  const log = (...args) => DEBUG && console.log("[DepositHome]", ...args);

  const ds = root.dataset || {};

  /* ==========================================================
   * 1) URL 설정 (dataset 우선, 없으면 기본값)
   * ========================================================== */
  const URLS = {
    page: ds.resetUrl || "/commission/deposit/",
    userDetail: ds.userDetailUrl || "/commission/api/user-detail/",
    summary: ds.depositSummaryUrl || "/commission/api/deposit-summary/",
    surety: ds.depositSuretyUrl || "/commission/api/deposit-surety/",
    other: ds.depositOtherUrl || "/commission/api/deposit-other/",
    supportPdf: ds.supportPdfUrl || "/commission/api/support-pdf/",
  };

  /* ==========================================================
   * 2) DOM refs
   * ========================================================== */
  const els = {
    supportPdfBtn: document.getElementById("supportPdfBtn"),
    resetBtn: document.getElementById("resetUserBtn"),
    empIdSpan: document.getElementById("target_emp_id"), // fallback only

    suretyTbody: document.getElementById("suretyTableBody"),
    otherTbody: document.getElementById("otherTableBody"),
  };

  /* ==========================================================
   * 3) Small Utils
   * ========================================================== */
  const toText = (v) => (v === null || v === undefined ? "" : String(v));

  const readTextOrValue = (el) => {
    if (!el) return "";
    if ("value" in el) {
      const v = String(el.value || "").trim();
      if (v) return v;
    }
    return String(el.textContent || "").trim();
  };

  const qsUser = () => new URL(window.location.href).searchParams.get("user") || "";

  const safeSetText = (node, text) => {
    if (!node) return;
    node.textContent = text === null || text === undefined || text === "" ? "-" : String(text);
  };

  const setSupportEnabled = (userId) => {
    if (!els.supportPdfBtn) return;
    els.supportPdfBtn.disabled = !String(userId || "").trim();
  };

  /* money/percent 안전 포맷 (문자열은 그대로 통과) */
  const comma = (v) => {
    const s = toText(v).trim();
    if (!s || s === "-" || s.toLowerCase() === "nan") return "-";

    const cleaned = s.replace(/,/g, "");
    const num = Number(cleaned);
    if (!Number.isFinite(num)) return s; // "정상/분급" 같은 문자열 방어
    return Math.trunc(num).toLocaleString("ko-KR");
  };

  const percent = (v) => {
    const s = toText(v).trim();
    if (!s || s === "-" || s.toLowerCase() === "nan") return "-";

    const cleaned = s.replace(/,/g, "");
    const num = Number(cleaned);
    if (!Number.isFinite(num)) return s;
    return `${num.toFixed(2)}%`;
  };

  /* HTML escape */
  const escapeHtml = (str) =>
    String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  /* ==========================================================
   * 4) Modal: ellipsis-cell 전체보기
   * ========================================================== */
  function openTextViewer(title, text) {
    const safeTitle = title || "전체 내용";
    const safeText = (text || "").toString();

    // Bootstrap 모달 없으면 alert fallback
    if (!window.bootstrap || !window.bootstrap.Modal) {
      alert(`${safeTitle}\n\n${safeText || "-"}`);
      return;
    }

    let modal = document.getElementById("textViewerModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "textViewerModal";
      modal.className = "modal fade";
      modal.tabIndex = -1;
      modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-lg">
          <div class="modal-content rounded-4">
            <div class="modal-header">
              <h6 class="modal-title fw-bold"></h6>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <pre class="mb-0 small" style="white-space:pre-wrap;word-break:break-word;"></pre>
            </div>
          </div>
        </div>`;
      document.body.appendChild(modal);
    }

    modal.querySelector(".modal-title").textContent = safeTitle;
    modal.querySelector("pre").textContent = safeText || "-";
    new bootstrap.Modal(modal).show();
  }

  function bindEllipsisClickOnce() {
    if (window.__depositEllipsisBound) return;
    window.__depositEllipsisBound = true;

    document.addEventListener("click", (e) => {
      const cell = e.target.closest(".ellipsis-cell");
      if (!cell) return;
      const full = String(cell.dataset.fullText || "").trim();
      const fallback = String(cell.textContent || "").trim();
      openTextViewer("전체 내용", full || fallback || "-");
    });
  }

  /* ==========================================================
   * 5) Fetch helpers
   * - 응답 구조가 달라도 최대한 흡수(unwrap)
   * ========================================================== */
  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const msg = data?.message || `요청 실패 (${res.status})`;
      throw new Error(msg);
    }
    if (data && data.ok === false) {
      throw new Error(data.message || "요청 실패");
    }
    return data;
  }

  function unwrapFirstObject(data, candidates = []) {
    if (!data || typeof data !== "object") return null;

    for (const k of candidates) {
      const v = data?.[k];
      if (v && typeof v === "object") return v;
    }

    for (const k of ["user", "summary", "data", "result", "payload", "item"]) {
      const v = data?.[k];
      if (v && typeof v === "object") return v;
    }
    return null;
  }

  function unwrapFirstArray(data, candidates = []) {
    if (!data || typeof data !== "object") return [];
    for (const k of candidates) {
      const v = data?.[k];
      if (Array.isArray(v)) return v;
    }
    for (const k of ["items", "results", "data", "list", "rows"]) {
      const v = data?.[k];
      if (Array.isArray(v)) return v;
    }
    return [];
  }

  const api = {
    async userDetail(userId) {
      const url = `${URLS.userDetail}?user=${encodeURIComponent(userId)}`;
      const data = await fetchJSON(url);
      return unwrapFirstObject(data, ["user", "data", "result", "item"]);
    },
    async summary(userId) {
      const url = `${URLS.summary}?user=${encodeURIComponent(userId)}`;
      const data = await fetchJSON(url);
      return unwrapFirstObject(data, ["summary", "data", "result", "item"]);
    },
    async surety(userId) {
      const url = `${URLS.surety}?user=${encodeURIComponent(userId)}`;
      const data = await fetchJSON(url);
      return unwrapFirstArray(data, ["items", "results", "data", "list"]);
    },
    async other(userId) {
      const url = `${URLS.other}?user=${encodeURIComponent(userId)}`;
      const data = await fetchJSON(url);
      return unwrapFirstArray(data, ["items", "results", "data", "list"]);
    },
  };

  /* ==========================================================
   * 6) data-bind 렌더 (legacy alias 흡수)
   * ========================================================== */
  const BIND_ALIAS = {
    // target.*
    "target.emp_id": "target.id",
    "target.join_date": "target.join_date_display",
    "target.leave_date": "target.retire_date_display",

    // summary.* legacy
    "summary.final_pay": "summary.final_payment",
    "summary.long_term": "summary.sales_total",
    "summary.loss_asset": "summary.maint_total",
    "summary.deposit_total": "summary.debt_total",
    "summary.etc_total": "summary.other_total",
    "summary.need_deposit": "summary.required_debt",
    "summary.final_extra_pay": "summary.final_excess_amount",
    "summary.month1": "summary.div_1m",
    "summary.month2": "summary.div_2m",
    "summary.month3": "summary.div_3m",
  };

  function resolveBindKey(key) {
    return BIND_ALIAS[key] || key;
  }

  function getByPath(obj, path) {
    const parts = String(path || "").split(".");
    let cur = obj;
    for (const p of parts) {
      if (!cur) return undefined;
      cur = cur[p];
    }
    return cur;
  }

  function renderBinds({ target, summary }) {
    const ctx = { target: target || {}, summary: summary || {} };

    root.querySelectorAll("[data-bind]").forEach((node) => {
      const rawKey = node.getAttribute("data-bind");
      const key = resolveBindKey(rawKey);
      const type = (node.getAttribute("data-type") || "").trim(); // money/percent/plain
      const v = getByPath(ctx, key);

      if (type === "percent") safeSetText(node, percent(v));
      else if (type === "money") safeSetText(node, comma(v));
      else safeSetText(node, toText(v).trim() || "-");
    });

    const uid = String(target?.id || "").trim();
    setSupportEnabled(uid);
  }

  /* ==========================================================
   * 7) 테이블 렌더 (surety / other)
   * ========================================================== */
  function renderSurety(items) {
    if (!els.suretyTbody) return;

    if (!items || items.length === 0) {
      els.suretyTbody.innerHTML = `
        <tr><td class="text-nowrap text-center" colspan="6">표시할 보증보험 내역이 없습니다.</td></tr>
      `;
      return;
    }

    els.suretyTbody.innerHTML = items
      .map((x) => {
        const policy = toText(x.policy_no || "").trim();
        const policyCell = policy
          ? `<span class="ellipsis-cell" data-full-text="${escapeHtml(policy)}">${escapeHtml(policy)}</span>`
          : "-";

        return `
          <tr>
            <td class="text-nowrap">${escapeHtml(x.product_name || "")}</td>
            <td class="text-nowrap">${policyCell}</td>
            <td class="text-nowrap text-end">${comma(x.amount)}</td>
            <td class="text-nowrap">${escapeHtml(x.status || "")}</td>
            <td class="text-nowrap">${escapeHtml(x.start_date || "-")}</td>
            <td class="text-nowrap">${escapeHtml(x.end_date || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderOther(items) {
    if (!els.otherTbody) return;

    if (!items || items.length === 0) {
      els.otherTbody.innerHTML = `
        <tr><td class="text-nowrap text-center" colspan="7">표시할 기타채권 내역이 없습니다.</td></tr>
      `;
      return;
    }

    els.otherTbody.innerHTML = items
      .map((x) => {
        const memo = toText(x.memo || "").trim();
        const memoCell = memo
          ? `<span class="ellipsis-cell" data-full-text="${escapeHtml(memo)}">${escapeHtml(memo)}</span>`
          : "-";

        return `
          <tr>
            <td class="text-nowrap">${escapeHtml(x.product_name || "")}</td>
            <td class="text-nowrap">${escapeHtml(x.product_type || "")}</td>
            <td class="text-nowrap text-end">${comma(x.amount)}</td>
            <td class="text-nowrap">${escapeHtml(x.status || "")}</td>
            <td class="text-nowrap">${escapeHtml(x.bond_no || "")}</td>
            <td class="text-nowrap">${escapeHtml(x.start_date || "-")}</td>
            <td class="text-nowrap">${memoCell}</td>
          </tr>
        `;
      })
      .join("");
  }

  function clearUI() {
    root.querySelectorAll("[data-bind]").forEach((n) => (n.textContent = "-"));

    if (els.suretyTbody) {
      els.suretyTbody.innerHTML = `
        <tr><td class="text-nowrap text-center" colspan="6">대상자를 선택하면 보증보험 내역이 표시됩니다.</td></tr>
      `;
    }
    if (els.otherTbody) {
      els.otherTbody.innerHTML = `
        <tr><td class="text-nowrap text-center" colspan="7">대상자를 선택하면 기타채권 내역이 표시됩니다.</td></tr>
      `;
    }
    setSupportEnabled("");
  }

  /* ==========================================================
   * 8) Main flow: load → render
   * ========================================================== */
  let currentUserId = "";

  async function loadAndRender(userId) {
    const uid = String(userId || "").trim();
    if (!uid) {
      currentUserId = "";
      clearUI();
      return;
    }

    currentUserId = uid;
    setSupportEnabled(uid);

    try {
      const [user, summary, surety, other] = await Promise.all([
        api.userDetail(uid),
        api.summary(uid),
        api.surety(uid),
        api.other(uid),
      ]);

      renderBinds({ target: user, summary });
      renderSurety(surety);
      renderOther(other);

      log("render ok", { uid, suretyCount: surety.length, otherCount: other.length });
    } catch (err) {
      console.error(err);
      alert(err?.message || "데이터 조회 중 오류가 발생했습니다.");
      // 기존 UX 유지: 일부라도 표시된 상태를 깨지 않기 위해 clearUI()는 호출하지 않음
    }
  }

  function pushUserToUrl(userId) {
    const uid = String(userId || "").trim();
    const url = new URL(window.location.href);
    if (uid) url.searchParams.set("user", uid);
    else url.searchParams.delete("user");
    window.history.pushState({}, "", url.toString());
  }

  /* ==========================================================
   * 9) Events
   * ========================================================== */
  function getSelectedUserIdFromEvent(e) {
    const d = e?.detail || {};
    return d.id || d.user_id || d.userId || d.user || d.empId || d.emp_id || d.employee_id || "";
  }

  function bindUserSelected() {
    const handler = (e) => {
      const userId = getSelectedUserIdFromEvent(e);
      if (!userId) return;

      pushUserToUrl(userId);
      loadAndRender(userId);
    };

    window.addEventListener("userSelected", handler);
    document.addEventListener("userSelected", handler);
  }

  function bindReset() {
    if (!els.resetBtn) return;
    els.resetBtn.addEventListener("click", () => {
      pushUserToUrl("");
      loadAndRender("");
    });
  }

  function bindSupportPdf() {
    if (!els.supportPdfBtn) return;

    els.supportPdfBtn.addEventListener("click", () => {
      const uid =
        String(currentUserId || "").trim() ||
        qsUser() ||
        readTextOrValue(els.empIdSpan);

      if (!uid || uid === "-") {
        alert("대상자를 먼저 선택해주세요.");
        return;
      }

      window.location.href = `${URLS.supportPdf}?user=${encodeURIComponent(uid)}`;
    });
  }

  window.addEventListener("popstate", () => {
    loadAndRender(qsUser());
  });

  /* ==========================================================
   * 10) Init
   * ========================================================== */
  function init() {
    bindEllipsisClickOnce();
    bindUserSelected();
    bindReset();
    bindSupportPdf();

    const initial = qsUser();
    if (initial) loadAndRender(initial);
    else clearUI();

    log("init", { URLS, initial });
  }

  init();
})();
