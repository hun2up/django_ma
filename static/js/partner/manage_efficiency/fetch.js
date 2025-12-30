// django_ma/static/js/partner/manage_efficiency/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";

let mainDT = null;
let delegationBound = false;

/* ============================================================
   Dataset helpers (템플릿 data- 키 변화에 안전하게)
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
  // manage_charts.html: data-data-fetch-url
  return dsUrl(["fetchUrl", "dataFetchUrl", "dataDataFetchUrl", "dataFetch"]);
}
function getUpdateProcessDateUrl() {
  // manage_charts.html: data-update-process-date-url
  return dsUrl(["updateProcessDateUrl", "dataUpdateProcessDateUrl"]);
}
function getDeleteUrl() {
  // manage_charts.html: data-data-delete-url
  return dsUrl(["deleteUrl", "dataDeleteUrl", "dataDataDeleteUrl"]);
}

function getUserGrade() {
  return String(els.root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

function canEditProcessDate() {
  const g = getUserGrade();
  return g === "superuser" || g === "main_admin";
}

function canDeleteRow(row) {
  // ✅ 서버에서도 권한 검사하지만, UI에서도 최소한으로 필터
  // 기존 정책: superuser/main_admin만 삭제 버튼 노출
  const g = getUserGrade();
  if (g === "superuser" || g === "main_admin") return true;

  // (옵션) requester 본인 삭제를 허용하려면 아래 주석 해제
  // if (g === "sub_admin") {
  //   return String(row?.requester_id || "") === String(window.currentUser?.id || "");
  // }

  return false;
}

/* ============================================================
   Escapes (XSS 방지)
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
   Render helpers
============================================================ */
function renderAfterCell(val) {
  const v = String(val ?? "").trim();
  if (!v) return "";
  return `<span class="cell-after">${escapeHtml(v)}</span>`;
}

function renderOrFlag(val) {
  return val ? "O" : "";
}

/**
 * ✅ 처리일자 스타일
 * - sub_admin: 텍스트만
 * - superuser/main_admin: date input
 */
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
   Server calls
============================================================ */
async function updateProcessDate(id, value) {
  const url = getUpdateProcessDateUrl();
  if (!url) throw new Error("update_process_date_url 누락 (data-update-process-date-url 확인)");

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({
      id,
      process_date: value || "",
      kind: "efficiency", // ✅ views.py ajax_update_process_date에서 kind로 분기
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `처리일자 저장 실패 (${res.status})`);
  }
  return data;
}

async function deleteefficiencyRow(id) {
  const url = getDeleteUrl();
  if (!url) throw new Error("delete_url 누락 (data-data-delete-url 확인)");

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({ id }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `삭제 실패 (${res.status})`);
  }
  return data;
}

/* ============================================================
   DataTables columns
   ✅ manage_charts.html mainTable (14열)과 1:1 매칭
============================================================ */
const MAIN_COLUMNS = [
  // 1~3 요청자
  { data: "requester_name", defaultContent: "" },
  { data: "requester_id", defaultContent: "" },
  { data: "requester_branch", defaultContent: "" },

  // 4~6 대상자
  { data: "target_name", defaultContent: "" },
  { data: "target_id", defaultContent: "" },
  { data: "target_branch", defaultContent: "" }, // 변경전 소속(서버 target_branch)

  // 7 변경후 소속(강조)
  { data: "chg_branch", defaultContent: "", render: (val) => renderAfterCell(val) },

  // 8 변경전 직급(서버 rank)
  { data: "rank", defaultContent: "" },

  // 9 변경후 직급(강조)
  { data: "chg_rank", defaultContent: "", render: (val) => renderAfterCell(val) },

  // 10 OR
  { data: "or_flag", defaultContent: false, render: (val) => renderOrFlag(!!val) },

  // 11 비고
  { data: "memo", defaultContent: "" },

  // 12 요청일자(서버 request_date)
  { data: "request_date", defaultContent: "" },

  // 13 처리일자
  {
    data: "process_date",
    orderable: false,
    searchable: false,
    render: renderProcessDateCell,
    defaultContent: "",
  },

  // 14 삭제
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
    const proc = (r.process_date || "").trim();

    tr.innerHTML = `
      <td>${escapeHtml(r.requester_name)}</td>
      <td>${escapeHtml(r.requester_id)}</td>
      <td>${escapeHtml(r.requester_branch)}</td>

      <td>${escapeHtml(r.target_name)}</td>
      <td>${escapeHtml(r.target_id)}</td>
      <td>${escapeHtml(r.target_branch)}</td>

      <td>${renderAfterCell(r.chg_branch)}</td>
      <td>${escapeHtml(r.rank)}</td>
      <td>${renderAfterCell(r.chg_rank)}</td>

      <td class="text-center">${renderOrFlag(!!r.or_flag)}</td>
      <td>${escapeHtml(r.memo)}</td>
      <td class="text-center">${escapeHtml(r.request_date)}</td>

      <td class="text-center">
        ${
          grade === "sub_admin"
            ? `<span>${escapeHtml(proc)}</span>`
            : `<input type="date"
                      class="form-control form-control-sm processDateInput"
                      data-id="${escapeAttr(r.id || "")}"
                      value="${escapeAttr(proc)}"
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
   - 처리일자 변경
   - 삭제 클릭
============================================================ */
function bindDelegationOnce() {
  if (delegationBound) return;
  delegationBound = true;

  // 처리일자 변경
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

  // 삭제 클릭
  document.addEventListener("click", async (e) => {
    const btn = e.target?.closest?.(".btnDeleteRow");
    if (!btn) return;
    if (!els.mainTable || !els.mainTable.contains(btn)) return;

    const id = String(btn.dataset.id || "").trim();
    if (!id) return;

    if (!confirm("해당 행을 삭제할까요?")) return;

    // UI 중복클릭 방지
    btn.disabled = true;

    showLoading("삭제 중...");
    try {
      await deleteefficiencyRow(id);

      // ✅ 삭제 후 재조회는 여기서 바로 수행(안전하고 일관됨)
      // (기존 delete.js/커스텀 이벤트 의존 제거)
      const y = String(els.year?.value || "").trim();
      const m = String(els.month?.value || "").trim();
      const ym = `${y}-${m.padStart(2, "0")}`;

      const branch =
        String(els.branch?.value || "").trim() ||
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
   Normalize (서버 키 변화에 안전하게)
   ✅ views.py ajax_fetch() 구조에 맞춰 흡수:
     - rank
     - or_flag
     - request_date
============================================================ */
function normalizeRow(row = {}) {
  return {
    id: row.id || "",

    requester_name: row.requester_name || row.rq_name || "",
    requester_id: row.requester_id || row.rq_id || "",
    requester_branch: row.requester_branch || row.rq_branch || "",

    target_name: row.target_name || row.tg_name || "",
    target_id: row.target_id || row.tg_id || "",
    target_branch: row.target_branch || row.tg_branch || "",

    // ✅ 변경후 데이터: chg_* 우선
    chg_branch: row.chg_branch || row.after_branch || row.new_branch || "",
    chg_rank: row.chg_rank || row.after_rank || row.new_rank || "",

    // ✅ 서버는 변경전 직급이 rank
    rank: row.rank || row.target_rank || row.tg_rank || "",

    // ✅ OR
    or_flag: !!row.or_flag,

    memo: row.memo || "",
    request_date: row.request_date || "",
    process_date: row.process_date || "",
  };
}

/* ============================================================
   Fetch
   - 호출: fetchData(ym, branch, meta?)  ← meta는 와도 무시
============================================================ */
export async function fetchData(ym, branch, _metaIgnored) {
  if (!els.root) return;

  bindDelegationOnce();

  const baseUrl = getFetchUrl();
  if (!baseUrl) {
    console.warn("[efficiency/fetch] fetchUrl 누락", els.root?.dataset);
    renderMain([]);
    return;
  }

  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("month", String(ym || "").trim());
  url.searchParams.set("branch", String(branch || "").trim());

  showLoading("데이터를 불러오는 중입니다...");
  try {
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const data = await res.json().catch(() => ({}));
    const rawRows = Array.isArray(data?.rows) ? data.rows : [];

    if (!res.ok || data.status !== "success") {
      renderMain([]);
      return;
    }

    const rows = rawRows.map(normalizeRow);
    renderMain(rows);
  } catch (err) {
    console.error("❌ [efficiency/fetch] 예외:", err);
    renderMain([]);
  } finally {
    hideLoading();
  }
}
