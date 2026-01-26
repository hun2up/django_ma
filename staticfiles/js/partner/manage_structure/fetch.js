// django_ma/static/js/partner/manage_structure/fetch.js
import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";

console.log("✅ [structure/fetch] LOADED", { url: import.meta?.url });

/* =========================================================
   State
========================================================= */
let mainDT = null;
let delegationBound = false;
let resizeBound = false;

/* =========================================================
   Dataset helpers
========================================================= */
function toStr(v) {
  return String(v ?? "").trim();
}

function dsUrl(keys = []) {
  const ds = els.root?.dataset;
  if (!ds) return "";
  for (const k of keys) {
    const v = ds[k];
    if (v && toStr(v)) return toStr(v);
  }
  return "";
}

function getFetchUrl() {
  // template: data-data-fetch-url => dataset.dataFetchUrl
  return dsUrl(["fetchUrl", "dataFetchUrl", "dataDataFetchUrl", "dataFetch"]);
}
function getUpdateProcessDateUrl() {
  return dsUrl(["updateProcessDateUrl", "dataUpdateProcessDateUrl", "dataUpdateProcessDate"]);
}
function getDeleteUrl() {
  return dsUrl(["deleteUrl", "dataDeleteUrl", "dataDataDeleteUrl", "dataDelete"]);
}

/* =========================================================
   Permission helpers
========================================================= */
function getUserGrade() {
  return toStr(els.root?.dataset?.userGrade || window.currentUser?.grade || "");
}
function canEditProcessDate() {
  const g = getUserGrade();
  return g === "superuser" || g === "head";
}
function canDeleteRow() {
  const g = getUserGrade();
  return g === "superuser" || g === "head";
}

/* =========================================================
   UI helpers
========================================================= */
function revealSections() {
  if (els.inputSection) els.inputSection.hidden = false;
  if (els.mainSheet) els.mainSheet.hidden = false;

  // DT 폭 계산은 “표시된 다음 프레임”에서 해야 안정적
  requestAnimationFrame(() => requestAnimationFrame(() => adjustDT()));
}

/* =========================================================
   Safe JSON (HTML 응답 대비)
========================================================= */
async function safeReadJson(res) {
  const text = await res.text().catch(() => "");
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {
      status: "error",
      message: "서버 응답이 JSON이 아닙니다.",
      _raw: text.slice(0, 300),
    };
  }
}

/* =========================================================
   XSS escape
========================================================= */
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

/* =========================================================
   Render helpers
========================================================= */
function renderAfterCell(val) {
  const v = toStr(val);
  if (!v) return "";
  return `<span class="cell-after">${escapeHtml(v)}</span>`;
}

function fmtRequester(name, id) {
  const n = toStr(name);
  const i = toStr(id);
  if (n && i) return `${n}(${i})`;
  return n || i || "";
}

function fmtPerson(name, id) {
  const n = toStr(name);
  const i = toStr(id);
  if (n && i) return `${n}(${i})`;
  return n || i || "";
}

/**
 * ✅ OR 컬럼: 체크박스(읽기전용) 렌더
 * - 정렬/검색 제외, 비활성
 */
function renderOrFlag(val) {
  const checked = !!val ? "checked" : "";
  return `
    <div class="form-check d-flex justify-content-center mb-0">
      <input class="form-check-input or-checkbox" type="checkbox" disabled ${checked}>
    </div>
  `;
}

function renderProcessDateCell(_value, _type, row) {
  const grade = getUserGrade();
  const val = toStr(row.process_date || "");

  // leader은 읽기만
  if (grade === "leader") return `<span>${escapeHtml(val)}</span>`;

  return `
    <input type="date"
           class="form-control form-control-sm processDateInput"
           data-id="${escapeAttr(row.id || "")}"
           value="${escapeAttr(val)}"
           ${canEditProcessDate() ? "" : "disabled"} />
  `;
}

function buildActionButtons(row) {
  if (!canDeleteRow()) return "";
  return `
    <button type="button"
            class="btn btn-sm btn-outline-danger btnDeleteRow"
            data-id="${escapeAttr(row.id || "")}">
      삭제
    </button>
  `;
}

/* =========================================================
   Server calls
========================================================= */
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
    body: JSON.stringify({ id, process_date: value || "", kind: "structure" }),
  });

  const data = await safeReadJson(res);
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `처리일자 저장 실패 (${res.status})`);
  }
  return data;
}

async function deleteStructureRow(id) {
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

  const data = await safeReadJson(res);
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `삭제 실패 (${res.status})`);
  }
  return data;
}

/* =========================================================
   DataTables columns (✅ 13 cols: 요청자 통합 반영)
========================================================= */
const MAIN_COLUMNS = [
  // 1) 요청자: requester_name + (requester_id)
  {
    data: null,
    defaultContent: "",
    render: (_v, _t, row) => escapeHtml(fmtPerson(row.requester_name, row.requester_id)),
  },

  // 2) 대상자: target_name + (target_id)
  {
    data: null,
    defaultContent: "",
    render: (_v, _t, row) => escapeHtml(fmtPerson(row.target_name, row.target_id)),
  },

  // 3) 소속(변경전) = target_branch
  { data: "target_branch", defaultContent: "" },

  // 4) 소속(변경후)
  { data: "chg_branch", defaultContent: "", render: (v) => renderAfterCell(v) },

  // 5) 직급(변경전)
  { data: "rank", defaultContent: "" },

  // 6) 직급(변경후)
  { data: "chg_rank", defaultContent: "", render: (v) => renderAfterCell(v) },

  // 7) OR
  {
    data: "or_flag",
    defaultContent: false,
    className: "or-cell",
    orderable: false,
    searchable: false,
    render: (v) => renderOrFlag(!!v),
  },

  // 8) 비고 (고정폭 + 말줄임 + title 툴팁)
  {
    data: "memo",
    defaultContent: "",
    render: (v) => {
      const raw = toStr(v);
      const safe = escapeHtml(raw);
      const title = escapeAttr(raw);
      return `<span class="memo-cell" title="${title}">${safe}</span>`;
    },
  },

  // 9) 요청일자
  { data: "request_date", defaultContent: "" },

  // 10) 처리일자
  {
    data: "process_date",
    orderable: false,
    searchable: false,
    render: renderProcessDateCell,
    defaultContent: "",
  },

  // 11) 삭제
  {
    data: "id",
    orderable: false,
    searchable: false,
    render: (_id, _t, row) => buildActionButtons(row),
    defaultContent: "",
  },
];

const MAIN_COLSPAN = MAIN_COLUMNS.length;

function canUseDataTables() {
  return !!(els.mainTable && window.jQuery && window.jQuery.fn?.DataTable);
}

function adjustDT() {
  if (!mainDT) return;
  try {
    mainDT.columns.adjust();
  } catch (_) {}
}

function bindResizeOnce() {
  if (resizeBound) return;
  resizeBound = true;

  let raf = 0;
  window.addEventListener("resize", () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => adjustDT());
  });
}

/**
 * ✅ DataTables는 “한 번 붙으면 컬럼 정의가 고정”
 * - 기존 DT 남아있으면 destroy(true) 후 재생성
 */
function ensureMainDT() {
  if (!canUseDataTables()) return null;

  const $ = window.jQuery;

  if (!mainDT && $.fn.DataTable.isDataTable(els.mainTable)) {
    try {
      $(els.mainTable).DataTable().destroy(true);
    } catch (_) {}
  }

  if (mainDT) return mainDT;

  mainDT = $(els.mainTable).DataTable({
    paging: true,
    searching: true,
    info: true,
    ordering: false,
    pageLength: 10,
    lengthChange: true,
    autoWidth: false,
    destroy: true,

    scrollX: true,
    scrollCollapse: true,

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

  bindResizeOnce();
  return mainDT;
}

/* =========================================================
   Fallback render (DT 미사용 시)
========================================================= */
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
    const proc = toStr(r.process_date || "");
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${escapeHtml(fmtPerson(r.requester_name, r.requester_id))}</td>
      <td>${escapeHtml(fmtPerson(r.target_name, r.target_id))}</td>
      <td>${escapeHtml(r.target_branch)}</td>

      <td>${renderAfterCell(r.chg_branch)}</td>
      <td>${escapeHtml(r.rank)}</td>
      <td>${renderAfterCell(r.chg_rank)}</td>

      <td class="or-cell">${renderOrFlag(!!r.or_flag)}</td>

      <td><span class="memo-cell" title="${escapeAttr(r.memo)}">${escapeHtml(r.memo)}</span></td>

      <td class="text-center">${escapeHtml(r.request_date)}</td>

      <td class="text-center">
        ${
          grade === "leader"
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
    adjustDT();
    return;
  }
  renderFallback(rows);
}

/* =========================================================
   Delegation (bind once)
========================================================= */
function bindDelegationOnce() {
  if (delegationBound) return;
  delegationBound = true;

  // 처리일자 변경
  document.addEventListener("change", async (e) => {
    const t = e.target;
    if (!t?.classList?.contains("processDateInput")) return;
    if (!els.mainTable || !els.mainTable.contains(t)) return;
    if (!canEditProcessDate()) return;

    const id = toStr(t.dataset.id || "");
    const value = toStr(t.value || "");
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

    const id = toStr(btn.dataset.id || "");
    if (!id) return;

    if (!confirm("해당 행을 삭제할까요?")) return;

    btn.disabled = true;
    showLoading("삭제 중...");
    try {
      await deleteStructureRow(id);

      // ✅ 현재 선택값 기준으로 재조회
      const y = toStr(els.year?.value || els.yearSelect?.value || "");
      const m = toStr(els.month?.value || els.monthSelect?.value || "");
      const ym = `${y}-${String(m).padStart(2, "0")}`;

      const branch =
        toStr(els.branch?.value || els.branchSelect?.value || "") ||
        toStr(window.currentUser?.branch || "") ||
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

/* =========================================================
   Normalize (서버 키 변화 흡수)
========================================================= */
function normalizeRow(row = {}) {
  return {
    id: row.id || "",

    requester_name: row.requester_name || row.rq_name || "",
    requester_id: row.requester_id || row.rq_id || "",
    requester_branch: row.requester_branch || row.rq_branch || "",

    target_name: row.target_name || row.tg_name || "",
    target_id: row.target_id || row.tg_id || "",
    target_branch: row.target_branch || row.tg_branch || "",

    chg_branch: row.chg_branch || row.after_branch || row.new_branch || "",
    chg_rank: row.chg_rank || row.after_rank || row.new_rank || "",

    rank: row.rank || row.target_rank || row.tg_rank || "",

    or_flag: !!row.or_flag,

    memo: row.memo || "",
    request_date: row.request_date || "",
    process_date: row.process_date || "",
  };
}

/* =========================================================
   Fetch (public)
========================================================= */
export async function fetchData(ym, branch) {
  if (!els.root) return;

  bindDelegationOnce();
  revealSections();

  const baseUrl = getFetchUrl();
  if (!baseUrl) {
    console.warn("⚠️ [structure/fetch] fetchUrl 누락", els.root?.dataset);
    renderMain([]);
    return;
  }

  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("month", toStr(ym));
  url.searchParams.set("branch", toStr(branch));

  showLoading("데이터를 불러오는 중입니다...");
  try {
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const data = await safeReadJson(res);
    const rawRows = Array.isArray(data?.rows) ? data.rows : [];

    if (!res.ok || data.status !== "success") {
      console.warn("⚠️ [structure/fetch] server error", { status: res.status, data });
      renderMain([]);
      return;
    }

    const rows = rawRows.map(normalizeRow);
    renderMain(rows);
  } catch (err) {
    console.error("❌ [structure/fetch] 예외:", err);
    renderMain([]);
  } finally {
    hideLoading();
  }
}
