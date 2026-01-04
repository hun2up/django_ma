/* django_ma/static/js/commission/deposit_home.js
 * Deposit Home - Target selection + metrics + surety + other + excel upload
 *
 * REFACTOR (2026-01-02)
 * - ✅ userSelected 이벤트 수신(window+document) + 모달 클릭 fallback 유지
 * - ✅ 주요지표(분급/계속분) DOM refs 포함
 * - ✅ inst_prev 키 불일치 흡수(inst_prev/instPrev)
 * - ✅ 회차 비율 포맷: 소수 2자리 고정(fmtRate)
 * - ✅ 보증보험 증권번호(policy_no) 렌더 반영
 * - ✅ 업로드 후: 타입별 즉시 리프레시 유지 + "통산손보" summary refresh 포함
 * - ✅ 업로드 성공 시: 업로드일자(업데이트 카드) 셀 즉시 갱신(템플릿 유연 대응)
 */
(() => {
  "use strict";

  const DEBUG = false;

  const root = document.getElementById("deposit-home");
  if (!root) return;

  const ds = root.dataset || {};
  const log = (...a) => DEBUG && console.log("[DepositHome]", ...a);

  /* ===============================
   * API
   * =============================== */
  const API_BASE = {
    userDetail: ds.userDetailUrl || "/commission/api/user-detail/",
    depositSummary: ds.depositSummaryUrl || "/commission/api/deposit-summary/",
    depositSurety: ds.depositSuretyUrl || "/commission/api/deposit-surety/",
    depositOther: ds.depositOtherUrl || "/commission/api/deposit-other/",
    resetUrl: ds.resetUrl || "/commission/deposit/",
  };

  const API = {
    userDetail: (u) => `${API_BASE.userDetail}?user=${encodeURIComponent(u)}`,
    depositSummary: (u) => `${API_BASE.depositSummary}?user=${encodeURIComponent(u)}`,
    depositSurety: (u) => `${API_BASE.depositSurety}?user=${encodeURIComponent(u)}`,
    depositOther: (u) => `${API_BASE.depositOther}?user=${encodeURIComponent(u)}`,
  };

  /* ===============================
   * DOM refs
   * =============================== */
  const els = {
    // person
    empId: document.getElementById("target_emp_id"),
    name: document.getElementById("target_name"),
    part: document.getElementById("target_part"),
    branch: document.getElementById("target_branch"),
    joinDate: document.getElementById("target_join_date"),
    retireDate: document.getElementById("target_retire_date"),

    // metrics (top)
    finalPayment: document.getElementById("metric_final_payment"),
    salesTotal: document.getElementById("metric_sales_total"),
    refundExpected: document.getElementById("metric_refund_expected"),
    payExpected: document.getElementById("metric_pay_expected"),
    maintTotal: document.getElementById("metric_maint_total"),

    debtTotal: document.getElementById("metric_debt_total"),
    suretyTotal: document.getElementById("metric_surety_total"),
    otherTotal: document.getElementById("metric_other_total"),
    requiredDebt: document.getElementById("metric_required_debt"),
    finalExcessAmount: document.getElementById("metric_final_excess_amount"),

    // div/inst metrics
    div1m: document.getElementById("metric_div_1m"),
    div2m: document.getElementById("metric_div_2m"),
    div3m: document.getElementById("metric_div_3m"),
    instCurrent: document.getElementById("metric_inst_current"),
    instPrev: document.getElementById("metric_inst_prev"),

    // round-rate metrics
    ns_13_round: document.getElementById("metric_ns_13_round"),
    ns_18_round: document.getElementById("metric_ns_18_round"),
    ls_13_round: document.getElementById("metric_ls_13_round"),
    ls_18_round: document.getElementById("metric_ls_18_round"),

    ns_18_total: document.getElementById("metric_ns_18_total"),
    ns_25_total: document.getElementById("metric_ns_25_total"),
    ls_18_total: document.getElementById("metric_ls_18_total"),
    ls_25_total: document.getElementById("metric_ls_25_total"),

    // due metrics
    ns_2_6_due: document.getElementById("metric_ns_2_6_due"),
    ns_2_13_due: document.getElementById("metric_ns_2_13_due"),
    ls_2_6_due: document.getElementById("metric_ls_2_6_due"),
    ls_2_13_due: document.getElementById("metric_ls_2_13_due"),

    // commission metrics
    comm_3m: document.getElementById("metric_comm_3m"),
    comm_6m: document.getElementById("metric_comm_6m"),
    comm_9m: document.getElementById("metric_comm_9m"),
    comm_12m: document.getElementById("metric_comm_12m"),

    // tables
    suretyTbody: document.getElementById("suretyTableBody"),
    otherTbody: document.getElementById("otherTableBody"),

    // actions / modals
    resetBtn: document.getElementById("resetUserBtn"),
    searchModal: document.getElementById("searchUserModal"),

    // excel upload
    uploadForm: document.getElementById("excelUploadForm"),
    uploadResult: document.getElementById("uploadResult"),
  };

  /* ===============================
   * utils
   * =============================== */
  const isNil = (v) => v === null || v === undefined;

  const setText = (el, v, fb = "-") => {
    if (!el) return;
    const s = isNil(v) ? "" : String(v).trim();
    el.textContent = s || fb;
  };

  const toNum = (v) => {
    if (isNil(v)) return NaN;
    const s = String(v).replace(/,/g, "").trim();
    const n = Number(s);
    return Number.isFinite(n) ? n : NaN;
  };

  const fmtInt = (v) => {
    const n = toNum(v);
    return Number.isFinite(n) ? new Intl.NumberFormat("ko-KR").format(n) : "-";
  };

  // 비율(예: 87.50) => 소수 2자리 고정
  const fmtRate = (v) => {
    if (isNil(v)) return "-";
    const s = String(v).replace(/,/g, "").trim();
    if (!s || s.toLowerCase() === "nan" || s.toLowerCase() === "none" || s === "-") return "-";
    const n = Number(s);
    return Number.isFinite(n) ? n.toFixed(2) : "-";
  };

  const escapeHTML = (v) => {
    const s = isNil(v) ? "" : String(v);
    return s
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  };

  const hideModal = (m) => {
    if (!m || !window.bootstrap) return;
    (bootstrap.Modal.getInstance(m) || new bootstrap.Modal(m)).hide();
  };

  async function fetchJson(url) {
    let r;
    try {
      r = await fetch(url, { credentials: "same-origin" });
    } catch (e) {
      throw new Error(`NETWORK_ERROR: ${e?.message || e}`);
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  function extractSelectedUser(detail) {
    const d = detail || {};
    const u = d.user || d.selected || d.data || d.payload || d.item || d || {};

    const id = String(
      u.id ||
        u.user_id ||
        u.pk ||
        u.emp_id ||
        u.employee_id ||
        u.tg_id ||
        u.target_id ||
        u.userid ||
        ""
    ).trim();

    const name = String(
      u.name ||
        u.user_name ||
        u.full_name ||
        u.emp_name ||
        u.employee_name ||
        u.tg_name ||
        ""
    ).trim();

    return { id, name, raw: u };
  }

  /* ===============================
   * fetchers
   * =============================== */
  const fetchUserDetail = (u) => fetchJson(API.userDetail(u)).then((d) => d.user || {});
  const fetchSummary = (u) => fetchJson(API.depositSummary(u)).then((d) => d.summary || {});
  const fetchSurety = (u) =>
    fetchJson(API.depositSurety(u))
      .then((d) => d.items || [])
      .catch(() => []);
  const fetchOther = (u) =>
    fetchJson(API.depositOther(u))
      .then((d) => d.items || [])
      .catch(() => []);

  /* ===============================
   * renderers
   * =============================== */
  function renderUser(u = {}) {
    setText(els.empId, u.id);
    setText(els.name, u.name);
    setText(els.part, u.part);
    setText(els.branch, u.branch);
    setText(els.joinDate, u.join_date_display);
    setText(els.retireDate, u.retire_date_display || "재직중");
  }

  function renderSummary(s = {}) {
    // 주요지표
    setText(els.finalPayment, fmtInt(s.final_payment));
    setText(els.salesTotal, fmtInt(s.sales_total));
    setText(els.refundExpected, fmtInt(s.refund_expected));
    setText(els.payExpected, fmtInt(s.pay_expected));
    setText(els.maintTotal, s.maint_total ?? "-");

    setText(els.debtTotal, fmtInt(s.debt_total));
    setText(els.suretyTotal, fmtInt(s.surety_total));
    setText(els.otherTotal, fmtInt(s.other_total));
    setText(els.requiredDebt, fmtInt(s.required_debt));
    setText(els.finalExcessAmount, fmtInt(s.final_excess_amount));

    // 분급/계속분(키 불일치 흡수)
    setText(els.div1m, s.div_1m ?? s.div1m ?? "-");
    setText(els.div2m, s.div_2m ?? s.div2m ?? "-");
    setText(els.div3m, s.div_3m ?? s.div3m ?? "-");
    setText(els.instCurrent, fmtInt(s.inst_current ?? s.instCurrent ?? 0));
    setText(els.instPrev, fmtInt(s.inst_prev ?? s.instPrev ?? 0));

    // 회차 비율
    setText(els.ns_13_round, fmtRate(s.ns_13_round));
    setText(els.ns_18_round, fmtRate(s.ns_18_round));
    setText(els.ls_13_round, fmtRate(s.ls_13_round));
    setText(els.ls_18_round, fmtRate(s.ls_18_round));

    setText(els.ns_18_total, fmtRate(s.ns_18_total));
    setText(els.ns_25_total, fmtRate(s.ns_25_total));
    setText(els.ls_18_total, fmtRate(s.ls_18_total));
    setText(els.ls_25_total, fmtRate(s.ls_25_total));

    // 응당
    setText(els.ns_2_6_due, fmtInt(s.ns_2_6_due));
    setText(els.ns_2_13_due, fmtInt(s.ns_2_13_due));
    setText(els.ls_2_6_due, fmtInt(s.ls_2_6_due));
    setText(els.ls_2_13_due, fmtInt(s.ls_2_13_due));

    // 수수료 지표
    setText(els.comm_3m, fmtInt(s.comm_3m));
    setText(els.comm_6m, fmtInt(s.comm_6m));
    setText(els.comm_9m, fmtInt(s.comm_9m));
    setText(els.comm_12m, fmtInt(s.comm_12m));
  }

  function renderSuretyTable(items) {
    if (!els.suretyTbody) return;

    if (!items || !items.length) {
      els.suretyTbody.innerHTML = `<tr><td colspan="6" class="text-center">보증보험 데이터가 없습니다.</td></tr>`;
      return;
    }

    els.suretyTbody.innerHTML = items
      .map((r) => {
        const product = escapeHTML(r.product_name || "-");
        const policyNo = escapeHTML(r.policy_no || r.policyNo || r.policy_number || "-");
        const status = escapeHTML(r.status || "-");
        const start = escapeHTML(r.start_date || "-");
        const end = escapeHTML(r.end_date || "-");

        return `
          <tr>
            <td>${product}</td>
            <td>${policyNo}</td>
            <td class="text-end">${fmtInt(r.amount)}</td>
            <td>${status}</td>
            <td>${start}</td>
            <td>${end}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderOtherTable(items) {
    if (!els.otherTbody) return;

    if (!items || !items.length) {
      els.otherTbody.innerHTML = `<tr><td colspan="7" class="text-center">기타채권 데이터가 없습니다.</td></tr>`;
      return;
    }

    els.otherTbody.innerHTML = items
      .map((r) => {
        const product = escapeHTML(r.product_name || "-");
        const type = escapeHTML(r.product_type || "-");
        const status = escapeHTML(r.status || "-");
        const bondNo = escapeHTML(r.bond_no || r.bond_number || r.debt_no || "-");
        const join = escapeHTML(r.start_date || r.join_date || "-");
        const memo = escapeHTML(r.memo || "-");

        return `
          <tr>
            <td>${product}</td>
            <td>${type}</td>
            <td class="text-end">${fmtInt(r.amount)}</td>
            <td>${status}</td>
            <td>${bondNo}</td>
            <td>${join}</td>
            <td>${memo}</td>
          </tr>
        `;
      })
      .join("");
  }

  /* ===============================
   * 업로드일자 UI 갱신 (유연 대응)
   * =============================== */
  function updateUploadDateUI(part, uploadType, dateStr) {
    if (!part || !uploadType || !dateStr) return;

    // 1) 가장 권장: data 속성 기반
    // 예: <span data-upload-date data-part="MA사업1부" data-upload-type="통산손보">-</span>
    let el =
      document.querySelector(
        `[data-upload-date][data-part="${CSS.escape(part)}"][data-upload-type="${CSS.escape(uploadType)}"]`
      ) ||
      document.querySelector(
        `[data-upload-date][data-part="${CSS.escape(part)}"][data-upload-type="${CSS.escape(uploadType)}"] *`
      );

    // 2) id 패턴 fallback
    // 예: id="upload_date__통산손보__MA사업1부" / "upload_date_통산손보_MA사업1부"
    if (!el) {
      const candidates = [
        `upload_date__${uploadType}__${part}`,
        `upload_date_${uploadType}_${part}`,
        `uploadDate__${uploadType}__${part}`,
        `uploadDate_${uploadType}_${part}`,
      ];
      for (const id of candidates) {
        const found = document.getElementById(id);
        if (found) {
          el = found;
          break;
        }
      }
    }

    // 3) 텍스트 매칭 fallback(마지막 수단)
    // "통산손보" 행에서 part를 같이 포함한 셀을 찾아봄
    if (!el) {
      const nodes = Array.from(document.querySelectorAll("[data-upload-type], .upload-date, td, span, div"));
      el =
        nodes.find((n) => {
          const t = (n.textContent || "").replace(/\s+/g, " ").trim();
          return t.includes(uploadType) && t.includes(part);
        }) || null;
    }

    if (el) {
      el.textContent = dateStr;
      log("upload date ui updated:", { part, uploadType, dateStr, el });
    } else {
      log("upload date ui not found:", { part, uploadType, dateStr });
    }
  }

  /* ===============================
   * selection
   * =============================== */
  let lastUser = "";
  let inFlight = null;

  async function applySelection(uid) {
    const id = String(uid || "").trim();
    if (!id) return;

    if (id === lastUser && inFlight) return;
    lastUser = id;

    const token = Symbol("req");
    inFlight = token;

    log("applySelection:", id);

    try {
      const [u, s, surety, other] = await Promise.all([
        fetchUserDetail(id),
        fetchSummary(id),
        fetchSurety(id),
        fetchOther(id),
      ]);

      if (inFlight !== token) return;

      renderUser(u);
      renderSummary(s);
      renderSuretyTable(surety);
      renderOtherTable(other);

      hideModal(els.searchModal);
    } catch (e) {
      console.error(e);
      alert("대상자 정보를 불러오지 못했습니다.");
    } finally {
      if (inFlight === token) inFlight = null;
    }
  }

  /* ===============================
   * event binding: userSelected
   * =============================== */
  function bindUserSelected() {
    if (window.__depositUserSelectedBound) return;
    window.__depositUserSelectedBound = true;

    const handler = (e) => {
      const { id } = extractSelectedUser(e?.detail);
      if (!id) return;
      applySelection(id);
    };

    window.addEventListener("userSelected", handler);
    document.addEventListener("userSelected", handler);

    log("userSelected bound (window+document)");
  }

  /* ===============================
   * modal fallback (click-to-pick)
   * =============================== */
  function bindModalPickFallback() {
    const modal = els.searchModal;
    if (!modal) return;
    if (window.__depositModalPickBound) return;
    window.__depositModalPickBound = true;

    const results = modal.querySelector("#searchResults") || modal;

    const pickFromText = (txt) => {
      const s = String(txt || "").replace(/\s+/g, " ").trim();
      const m = s.match(/\b\d{4,}\b/);
      return m ? m[0] : "";
    };

    const pickFromOnclick = (el) => {
      const oc = el?.getAttribute?.("onclick") || "";
      if (!oc) return "";
      const m = oc.match(/['"](\d{4,})['"]|(\b\d{4,}\b)/);
      return m && (m[1] || m[2]) ? String(m[1] || m[2]).trim() : "";
    };

    const pickFromAttr = (el) => {
      if (!el?.getAttribute) return "";
      const keys = ["data-user-id", "data-emp-id", "data-id", "data-userid", "data-pk"];
      for (const k of keys) {
        const v = el.getAttribute(k);
        if (v && String(v).trim()) return String(v).trim();
      }
      return "";
    };

    const pickFromDataset = (el) => {
      if (!el) return "";
      const d = el.dataset || {};

      const jsonStr = d.user || d.item || d.payload || d.data || "";
      if (jsonStr) {
        try {
          const obj = JSON.parse(jsonStr);
          const id =
            obj?.id || obj?.user_id || obj?.pk || obj?.emp_id || obj?.employee_id || obj?.tg_id;
          if (id) return String(id).trim();
        } catch (_) {}
      }

      const direct =
        d.userId ||
        d.userid ||
        d.user_id ||
        d.empId ||
        d.emp_id ||
        d.employeeId ||
        d.employee_id ||
        d.pk ||
        d.id ||
        d.tgId ||
        d.tg_id;

      return direct ? String(direct).trim() : "";
    };

    const extractIdFromElement = (el) => {
      if (!el) return "";

      let id =
        pickFromDataset(el) ||
        pickFromAttr(el) ||
        pickFromOnclick(el) ||
        (el.value ? String(el.value).trim() : "");

      if (id) return id;

      let p = el;
      for (let i = 0; i < 8 && p; i++) {
        id = pickFromDataset(p) || pickFromAttr(p) || pickFromOnclick(p);
        if (id) return id;
        p = p.parentElement;
      }

      const row = el.closest?.("tr, li, .list-group-item, .card, .row, .col, .result-item");
      id = pickFromDataset(row) || pickFromAttr(row) || pickFromOnclick(row);
      if (id) return id;

      if (row) {
        id = pickFromText(row.textContent);
        if (id) return id;
      }
      return pickFromText(el.textContent);
    };

    results.addEventListener("click", (ev) => {
      const target = ev.target?.closest?.("*");
      if (!target) return;

      const id = extractIdFromElement(target);
      if (!id) return;

      log("picked from modal click:", id, target);
      applySelection(id);
    });

    log("modal pick fallback bound (results delegation)");
  }

  /* ===============================
   * reset
   * =============================== */
  function bindReset() {
    els.resetBtn?.addEventListener("click", () => {
      window.location.href = API_BASE.resetUrl;
    });
  }

  /* ===============================
   * excel upload
   * =============================== */
  function bindExcelUpload() {
    if (!els.uploadForm) return;
    if (els.uploadForm.dataset.bound === "1") return;
    els.uploadForm.dataset.bound = "1";

    els.uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fd = new FormData(els.uploadForm);

      let r;
      try {
        r = await fetch(els.uploadForm.action, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
      } catch (err) {
        console.error(err);
        if (els.uploadResult) els.uploadResult.textContent = "네트워크 오류";
        return;
      }

      const d = await r.json().catch(() => ({}));
      if (!r.ok || !d.ok) {
        if (els.uploadResult) els.uploadResult.textContent = d.message || "업로드 실패";
        return;
      }

      if (els.uploadResult) els.uploadResult.textContent = d.message || "업로드 완료";

      // ✅ 업로드일자 UI 즉시 갱신
      updateUploadDateUI(d.part, d.upload_type, d.uploaded_date);

      // ✅ 업로드 후 현재 대상자 있으면 즉시 리프레시
      try {
        if (lastUser) {
          const summaryRefreshTypes = new Set([
            "최종지급액",
            "보증증액",
            "응당생보",
            "응당손보",
            "통산손보", // ✅ 추가 (summary에 들어감)
          ]);

          if (summaryRefreshTypes.has(d.upload_type)) {
            renderSummary(await fetchSummary(lastUser));
          } else if (d.upload_type === "보증보험") {
            renderSuretyTable(await fetchSurety(lastUser));
          } else if (d.upload_type === "기타채권") {
            renderOtherTable(await fetchOther(lastUser));
          }
        }
      } catch (err) {
        console.warn("post-upload refresh failed:", err);
      }

      // 토스트
      if (window.bootstrap) {
        const t = document.getElementById("uploadToast");
        if (t) new bootstrap.Toast(t).show();
      }
    });
  }

  /* ===============================
   * init
   * =============================== */
  function init() {
    bindUserSelected();
    bindModalPickFallback();
    bindReset();
    bindExcelUpload();
    log("init done");
  }

  init();
})();
