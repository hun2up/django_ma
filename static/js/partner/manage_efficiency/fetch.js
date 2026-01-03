// django_ma/static/js/partner/manage_efficiency/fetch.js
//
// ✅ Final Refactor (2026-01-01)
// - superuser 메인시트 hidden 이슈 방지: fetchData에서 섹션 오픈 강제
// - 응답 포맷 유연화: rows/data/results/list/items 모두 흡수
// - res.json 실패 대비: text→json 파싱
// - 실패 시에도 빈 테이블 렌더 + 섹션 오픈
// - DataTables/fallback 안전 유지
// - updateProcessDate/delete: credentials same-origin + JSON 파싱 안전

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";

let mainDT = null;
let delegationBound = false;

/* ============================================================
   DOM fallback (mainSheet visible)
============================================================ */
function ensureSectionsVisible() {
  const inputSection = els.inputSection || document.getElementById("inputSection");
  const mainSheet = els.mainSheet || document.getElementById("mainSheet");

  if (inputSection) inputSection.hidden = false;
  if (mainSheet) mainSheet.hidden = false;
}

/* ============================================================
   Dataset helpers
============================================================ */
function dsUrl(keys = []) {
  const ds = els.root?.dataset;
  if (!ds) return "";
  for (const k of keys) {
    const v = ds[k];
    if (v && String(v).trim()) return String(v).trim();
  }
  return "";
}

function getFetchUrl() {
  return dsUrl(["fetchUrl", "dataFetchUrl", "dataDataFetchUrl", "dataFetch"]);
}
function getUpdateProcessDateUrl() {
  return dsUrl(["updateProcessDateUrl", "dataUpdateProcessDateUrl", "dataUpdateProcessDate"]);
}
function getDeleteUrl() {
  return dsUrl(["deleteUrl", "dataDeleteUrl", "dataDataDeleteUrl", "dataDelete"]);
}

function getUserGrade() {
  return String(els.root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

function canEditProcessDate() {
  const g = getUserGrade();
  return g === "superuser" || g === "main_admin";
}

function canDeleteRow(_row) {
  const g = getUserGrade();
  return g === "superuser" || g === "main_admin";
}

/* ============================================================
   Escapes (XSS)
============================================================ */
function escapeHtml(v) {
  const s = String(v ?? "");
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function escapeAttr(v) {
  return escapeHtml(v);
}

/* ============================================================
   ✅ 금액/세액 포맷/계산
============================================================ */
function toInt(v) {
  const n = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}
function formatIntComma(n) {
  const x = Number(n);
  if (!Number.isFinite(x) || x === 0) return "0";
  return String(Math.trunc(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
function calcTaxInt(amountInt) {
  return Math.floor(Number(amountInt || 0) * 0.033);
}

/* ============================================================
   Render helpers
============================================================ */
function renderProcessDateCell(_value, _type, row) {
  const grade = getUserGrade();
  const val = (row.process_date || "").trim();

  if (grade === "sub_admin") {
    return `<span>${escapeHtml(val)}</span>`;
  }

  const disabledAttr = canEditProcessDate() ? "" : "disabled";
  return `
    <input type="date"
           class="form-control form-control-sm processDateInput"
           data-id="${escapeAttr(row.id || "")}"
           value="${escapeAttr(val)}"
           ${disabledAttr} />
  `;
}

function buildActionButtons(row) {
  if (!canDeleteRow(row)) return "";
  return `
    <button type="button"
            class="btn btn-sm btn-outline-danger btnDeleteRow"
            data-id="${escapeAttr(row.id || "")}">
      삭제
    </button>
  `;
}

/* ============================================================
   Server calls (safe)
============================================================ */
async function safeReadJson(res) {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    console.error("❌ 서버가 JSON이 아닌 응답 반환:", { status: res.status, text });
    return { _raw: text };
  }
}

async function updateProcessDate(id, value) {
  const url = getUpdateProcessDateUrl();
  if (!url) throw new Error("update_process_date_url 누락");

  const res = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({
      id,
      process_date: value || "",
      kind: "efficiency",
    }),
  });

  const data = await safeReadJson(res);
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `처리일자 저장 실패 (${res.status})`);
  }
  return data;
}

async function deleteEfficiencyRow(id) {
  const url = getDeleteUrl();
  if (!url) throw new Error("delete_url 누락");

  const res = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({ id, kind: "efficiency" }),
  });

  const data = await safeReadJson(res);
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `삭제 실패 (${res.status})`);
  }
  return data;
}

/* ============================================================
   DataTables columns
   (요청자/사번/소속/구분/금액/세액/공제자명/공제자사번/지급자명/지급자사번/내용/요청일자/처리일자/삭제)
============================================================ */
const MAIN_COLUMNS = [
  { data: "rq_name", defaultContent: "" },
  { data: "rq_id", defaultContent: "" },
  { data: "rq_branch", defaultContent: "" },

  { data: "category", defaultContent: "" },

  {
    data: "amount",
    defaultContent: 0,
    render: (v) => formatIntComma(toInt(v)),
  },

  {
    data: "tax",
    defaultContent: "",
    render: (_v, _t, row) => {
      const amount = toInt(row?.amount);
      const tax = calcTaxInt(amount);
      return formatIntComma(tax);
    },
  },

  { data: "ded_name", defaultContent: "" },
  { data: "ded_id", defaultContent: "" },
  { data: "pay_name", defaultContent: "" },
  { data: "pay_id", defaultContent: "" },

  { data: "content", defaultContent: "" },

  { data: "request_date", defaultContent: "" },

  {
    data: "process_date",
    orderable: false,
    searchable: false,
    render: renderProcessDateCell,
    defaultContent: "",
  },

  {
    data: "id",
    orderable: false,
    searchable: false,
    render: (_id, _type, row) => buildActionButtons(row),
    defaultContent: "",
  },
];

const MAIN_COLSPAN = MAIN_COLUMNS.length;

/* ============================================================
   DataTables initialize / fallback
============================================================ */
function canUseDataTables() {
  return !!(els.mainTable && window.jQuery && window.jQuery.fn?.DataTable);
}

function ensureMainDT() {
  if (!canUseDataTables()) return null;
  if (mainDT) return mainDT;

  mainDT = window.jQuery(els.mainTable).DataTable({
    paging: true,
    searching: true,
    info: true,
    ordering: false,
    pageLength: 10,
    lengthChange: true,
    autoWidth: false,
    destroy: true,
    language: {
      emptyTable: "데이터가 없습니다.",
      search: "검색:",
      lengthMenu: "_MENU_개씩 보기",
      info: "_TOTAL_건 중 _START_ ~ _END_",
      infoEmpty: "0건",
      paginate: { previous: "이전", next: "다음" },
    },
    columns: MAIN_COLUMNS,
  });

  return mainDT;
}

function renderFallback(rows) {
  const tbody = els.mainTable?.querySelector("tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (!rows?.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="${MAIN_COLSPAN}" class="text-center text-muted">데이터가 없습니다.</td>`;
    tbody.appendChild(tr);
    return;
  }

  const grade = getUserGrade();

  rows.forEach((r) => {
    const tr = document.createElement("tr");
    const amount = toInt(r.amount);
    const tax = calcTaxInt(amount);

    tr.innerHTML = `
      <td>${escapeHtml(r.rq_name)}</td>
      <td>${escapeHtml(r.rq_id)}</td>
      <td>${escapeHtml(r.rq_branch)}</td>

      <td>${escapeHtml(r.category)}</td>
      <td class="text-end">${escapeHtml(formatIntComma(amount))}</td>
      <td class="text-end">${escapeHtml(formatIntComma(tax))}</td>

      <td>${escapeHtml(r.ded_name)}</td>
      <td>${escapeHtml(r.ded_id)}</td>
      <td>${escapeHtml(r.pay_name)}</td>
      <td>${escapeHtml(r.pay_id)}</td>

      <td>${escapeHtml(r.content)}</td>
      <td class="text-center">${escapeHtml(r.request_date)}</td>

      <td class="text-center">
        ${
          grade === "sub_admin"
            ? `<span>${escapeHtml(r.process_date || "")}</span>`
            : `<input type="date"
                      class="form-control form-control-sm processDateInput"
                      data-id="${escapeAttr(r.id || "")}"
                      value="${escapeAttr(r.process_date || "")}"
                      ${canEditProcessDate() ? "" : "disabled"} />`
        }
      </td>

      <td class="text-center">${buildActionButtons(r)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderMain(rows) {
  const dt = ensureMainDT();
  if (dt) {
    dt.clear();
    if (rows?.length) dt.rows.add(rows);
    dt.draw();
    return;
  }
  renderFallback(rows);
}

/* ============================================================
   Delegation (once)
============================================================ */
function bindDelegationOnce() {
  if (delegationBound) return;
  delegationBound = true;

  document.addEventListener("change", async (e) => {
    const t = e.target;
    if (!t?.classList?.contains("processDateInput")) return;
    if (!els.mainTable || !els.mainTable.contains(t)) return;
    if (!canEditProcessDate()) return;

    const id = String(t.dataset.id || "").trim();
    const value = String(t.value || "").trim();
    if (!id) return;

    showLoading("처리일자 저장 중...");
    try {
      await updateProcessDate(id, value);
    } catch (err) {
      console.error(err);
      (alertBox || alert)(err?.message || "처리일자 저장 실패");
    } finally {
      hideLoading();
    }
  });

  document.addEventListener("click", async (e) => {
    const btn = e.target?.closest?.(".btnDeleteRow");
    if (!btn) return;
    if (!els.mainTable || !els.mainTable.contains(btn)) return;

    const id = String(btn.dataset.id || "").trim();
    if (!id) return;
    if (!confirm("해당 행을 삭제할까요?")) return;

    btn.disabled = true;

    showLoading("삭제 중...");
    try {
      await deleteEfficiencyRow(id);

      const y = String((els.year || document.getElementById("yearSelect"))?.value || "").trim();
      const m = String((els.month || document.getElementById("monthSelect"))?.value || "").trim();
      const ym = `${y}-${m.padStart(2, "0")}`;

      const branch =
        String((els.branch || document.getElementById("branchSelect"))?.value || "").trim() ||
        String(window.currentUser?.branch || "").trim() ||
        "";

      await fetchData(ym, branch);
    } catch (err) {
      console.error(err);
      (alertBox || alert)(err?.message || "삭제 실패");
    } finally {
      hideLoading();
      btn.disabled = false;
    }
  });
}

/* ============================================================
   Normalize (서버 키 변화에 안전)
============================================================ */
function normalizeRow(row = {}) {
  const amount = toInt(row.amount ?? row.amt ?? row.price ?? 0);

  return {
    id: row.id || "",

    rq_name: row.rq_name || row.requester_name || "",
    rq_id: row.rq_id || row.requester_id || "",
    rq_branch: row.rq_branch || row.requester_branch || "",

    category: row.category || row.kind || "",
    amount,

    tax: row.tax || row.tax_amount || "",

    ded_name: row.ded_name || "",
    ded_id: row.ded_id || "",
    pay_name: row.pay_name || "",
    pay_id: row.pay_id || "",

    content: row.content || row.memo || "",
    request_date: row.request_date || row.created_at || "",
    process_date: row.process_date || "",
  };
}

/* ============================================================
   ✅ rows extraction (superuser 응답 포맷 달라도 흡수)
============================================================ */
function pickRows(data) {
  const candidates = [
    data?.rows,
    data?.data,
    data?.results,
    data?.list,
    data?.items,
  ];
  for (const c of candidates) {
    if (Array.isArray(c)) return c;
  }
  return [];
}

/* ============================================================
   Fetch
============================================================ */
export async function fetchData(ym, branch, _metaIgnored) {
  if (!els.root) return;

  bindDelegationOnce();

  const baseUrl = getFetchUrl();
  if (!baseUrl) {
    console.warn("[efficiency/fetch] fetchUrl 누락", els.root?.dataset);
    // ✅ 섹션은 열어주고 빈 테이블 렌더
    ensureSectionsVisible();
    renderMain([]);
    return;
  }

  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("month", String(ym || "").trim());
  url.searchParams.set("branch", String(branch || "").trim());

  showLoading("데이터를 불러오는 중입니다...");
  try {
    const res = await fetch(url.toString(), {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const data = await safeReadJson(res);

    // ✅ 핵심: superuser 포함 “항상 섹션 오픈”
    ensureSectionsVisible();

    if (!res.ok || data.status !== "success") {
      console.warn("⚠️ fetch 실패 또는 status!=success", { status: res.status, data });
      renderMain([]);
      return;
    }

    const rawRows = pickRows(data);
    const rows = rawRows.map(normalizeRow);

    renderMain(rows);
  } catch (err) {
    console.error("❌ [efficiency/fetch] 예외:", err);
    ensureSectionsVisible();
    renderMain([]);
  } finally {
    hideLoading();
  }
}
