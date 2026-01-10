/* django_ma/static/js/commission/deposit_home.js
 * Deposit Home (채권현황) - FINAL (FETCH + RENDER + SUPPORT PDF)
 *
 * ✅ 핵심
 * - 페이지: /commission/deposit/ 단일
 * - 대상자 선택(userSelected) → pushState로 URL만 바꾸고 즉시 fetch&render (no reload)
 * - API 응답(권장):
 *   - user-detail     : { ok:true, user:{...} }  (또는 data/result/item 래핑도 허용)
 *   - deposit-summary : { ok:true, summary:{...} } (또는 data/result/item 래핑도 허용)
 *   - surety-list     : { ok:true, items:[...] }  (또는 results/data/list/rows 래핑도 허용)
 *   - other-list      : { ok:true, items:[...] }  (또는 results/data/list/rows 래핑도 허용)
 *
 * ✅ FIX
 * - 템플릿 data-bind(legacy 키) ↔ API 키 불일치 → alias로 흡수
 * - tbody id: suretyTableBody / otherTableBody 렌더
 * - 분급/정상 같은 문자열이 money로 들어와도 안전 표시
 * - ellipsis-cell 클릭 시 전체 텍스트 뷰어
 */

(() => {
  "use strict";

  const DEBUG = false;

  const root = document.getElementById("deposit-home");
  if (!root) return;

  const ds = root.dataset || {};
  const log = (...a) => DEBUG && console.log("[DepositHome]", ...a);

  /* ===============================
   * URLs
   * =============================== */
  const URLS = {
    page: ds.resetUrl || "/commission/deposit/",
    userDetail: ds.userDetailUrl || "/commission/api/user-detail/",
    summary: ds.depositSummaryUrl || "/commission/api/deposit-summary/",
    surety: ds.depositSuretyUrl || "/commission/api/deposit-surety/",
    other: ds.depositOtherUrl || "/commission/api/deposit-other/",
    supportPdf: ds.supportPdfUrl || "/commission/api/support-pdf/",
  };

  /* ===============================
   * DOM refs
   * =============================== */
  const els = {
    supportPdfBtn: document.getElementById("supportPdfBtn"),
    resetBtn: document.getElementById("resetUserBtn"),
    // (선택) 화면 어딘가에 대상 사번이 찍혀있을 수도 있으니 fallback로만 사용
    empIdSpan: document.getElementById("target_emp_id"),

    suretyTbody: document.getElementById("suretyTableBody"),
    otherTbody: document.getElementById("otherTableBody"),
  };

  /* ===============================
   * Utils
   * =============================== */
  const qsUser = () => new URL(window.location.href).searchParams.get("user") || "";

  const toText = (v) => (v === null || v === undefined ? "" : String(v));

  const readElValue = (el) => {
    if (!el) return "";
    if ("value" in el) {
      const v = String(el.value || "").trim();
      if (v) return v;
    }
    return String(el.textContent || "").trim();
  };

  const comma = (n) => {
    const s = toText(n).trim();
    if (!s || s === "-" || s.toLowerCase() === "nan") return "-";
    // 숫자만 처리
    const cleaned = s.replace(/,/g, "");
    const num = Number(cleaned);
    if (!Number.isFinite(num)) return s; // "정상/분급" 같은 문자열은 그대로
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

  const safeSetText = (node, text) => {
    if (!node) return;
    node.textContent =
      text === null || text === undefined || text === "" ? "-" : String(text);
  };

  const setSupportEnabled = (userId) => {
    if (!els.supportPdfBtn) return;
    els.supportPdfBtn.disabled = !String(userId || "").trim();
  };

  const getSelectedUserIdFromEvent = (e) => {
    const d = e?.detail || {};
    return (
      d.id ||
      d.user_id ||
      d.userId ||
      d.user ||
      d.empId ||
      d.emp_id ||
      d.employee_id ||
      ""
    );
  };

  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function openTextViewer(title, text) {
    const safeTitle = title || "전체 내용";
    const safeText = (text || "").toString();

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

  function bindEllipsisClick() {
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

  /* ===============================
   * Fetch helpers
   * =============================== */
  async function fetchJSON(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

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

  // ✅ 공통 언랩(응답 구조가 달라도 최대한 흡수)
  function unwrapFirstObject(data, candidates = []) {
    if (!data || typeof data !== "object") return null;

    // 1) 후보 키들 우선 탐색
    for (const k of candidates) {
      const v = data?.[k];
      if (v && typeof v === "object") return v;
    }

    // 2) 흔한 래핑 키 fallback
    const common = ["user", "summary", "data", "result", "payload", "item"];
    for (const k of common) {
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

    const common = ["items", "results", "data", "list", "rows"];
    for (const k of common) {
      const v = data?.[k];
      if (Array.isArray(v)) return v;
    }

    return [];
  }

  async function loadUserDetail(userId) {
    const url = `${URLS.userDetail}?user=${encodeURIComponent(userId)}`;
    const data = await fetchJSON(url);

    // ✅ {user:{}} / {data:{}} / {result:{}} / {item:{}} 모두 허용
    return unwrapFirstObject(data, ["user", "data", "result", "item"]);
  }

  async function loadSummary(userId) {
    const url = `${URLS.summary}?user=${encodeURIComponent(userId)}`;
    const data = await fetchJSON(url);

    // ✅ {summary:{}} / {data:{}} / {result:{}} 등 흡수
    return unwrapFirstObject(data, ["summary", "data", "result", "item"]);
  }

  async function loadSurety(userId) {
    const url = `${URLS.surety}?user=${encodeURIComponent(userId)}`;
    const data = await fetchJSON(url);

    // ✅ {items:[]} / {results:[]} / {data:[]} 등 흡수
    return unwrapFirstArray(data, ["items", "results", "data", "list"]);
  }

  async function loadOther(userId) {
    const url = `${URLS.other}?user=${encodeURIComponent(userId)}`;
    const data = await fetchJSON(url);

    return unwrapFirstArray(data, ["items", "results", "data", "list"]);
  }

  /* ===============================
   * Render: data-bind (legacy alias)
   * =============================== */
  const BIND_ALIAS = {
    // target.*
    "target.emp_id": "target.id",
    "target.join_date": "target.join_date_display",
    "target.leave_date": "target.retire_date_display",

    // summary.* (템플릿 legacy)
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

  function getByPath(obj, path) {
    const parts = String(path || "").split(".");
    let cur = obj;
    for (const p of parts) {
      if (!cur) return undefined;
      cur = cur[p];
    }
    return cur;
  }

  function resolveBindKey(key) {
    return BIND_ALIAS[key] || key;
  }

  function renderBinds({ target, summary }) {
    const ctx = { target: target || {}, summary: summary || {} };

    const nodes = root.querySelectorAll("[data-bind]");
    nodes.forEach((node) => {
      const rawKey = node.getAttribute("data-bind");
      const key = resolveBindKey(rawKey);
      const type = (node.getAttribute("data-type") || "").trim(); // money/percent/plain
      const v = getByPath(ctx, key);

      if (type === "percent") {
        safeSetText(node, percent(v));
      } else if (type === "money") {
        // 템플릿에서 month1 같은 문자열도 money로 들어온 케이스 방어
        safeSetText(node, comma(v));
      } else {
        safeSetText(node, toText(v).trim() || "-");
      }
    });

    // support 버튼 활성화
    const uid = String(target?.id || "").trim();
    setSupportEnabled(uid);
  }

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
    // data-bind 영역 전부 "-"
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

  /* ===============================
   * Main load
   * =============================== */
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
        loadUserDetail(uid),
        loadSummary(uid),
        loadSurety(uid),
        loadOther(uid),
      ]);

      renderBinds({ target: user, summary });
      renderSurety(surety);
      renderOther(other);

      log("render ok", {
        uid,
        user,
        summary,
        suretyCount: surety.length,
        otherCount: other.length,
      });
    } catch (err) {
      console.error(err);
      alert(err?.message || "데이터 조회 중 오류가 발생했습니다.");
      // 일부라도 표기된 상태를 깨지 않게 clear는 안 함
    }
  }

  function pushUserToUrl(userId) {
    const uid = String(userId || "").trim();
    const url = new URL(window.location.href);
    if (uid) url.searchParams.set("user", uid);
    else url.searchParams.delete("user");
    window.history.pushState({}, "", url.toString());
  }

  /* ===============================
   * Bindings
   * =============================== */
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
        String(currentUserId || "").trim() || qsUser() || readElValue(els.empIdSpan);

      if (!uid || uid === "-") {
        alert("대상자를 먼저 선택해주세요.");
        return;
      }

      const url = `${URLS.supportPdf}?user=${encodeURIComponent(uid)}`;
      window.location.href = url;
    });
  }

  window.addEventListener("popstate", () => {
    // 뒤로가기/앞으로가기 시 URL의 user 기준으로 다시 렌더
    loadAndRender(qsUser());
  });

  /* ===============================
   * Init
   * =============================== */
  function init() {
    bindEllipsisClick();
    bindUserSelected();
    bindReset();
    bindSupportPdf();

    const initial = qsUser();
    if (initial) {
      loadAndRender(initial);
    } else {
      clearUI();
    }

    log("init", { URLS, initial });
  }

  init();
})();
