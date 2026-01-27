// django_ma/static/js/partner/manage_rate/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { resetInputSection } from "./input_rows.js";

let mainDT = null;
let delegationBound = false;
let resizeBound = false;

/* =========================================================
   Dataset/URL helpers (키 변화/오타 대응)
========================================================= */
function toDashed(camel) {
  return String(camel || "").replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);
}

function pickDatasetUrl(root, keys = []) {
  if (!root) return "";

  const ds = root.dataset || {};
  for (const k of keys) {
    const v = ds?.[k];
    if (v && String(v).trim()) return String(v).trim();
  }

  // data-xxx attribute fallback
  for (const k of keys) {
    const attr = `data-${toDashed(k)}`;
    const v = root.getAttribute?.(attr);
    if (v && String(v).trim()) return String(v).trim();
  }

  return "";
}

function getFetchBaseUrl() {
  return pickDatasetUrl(els.root, ["fetchUrl", "dataFetchUrl", "fetchURL", "dataFetchURL"]);
}

function getUpdateProcessDateUrl() {
  return pickDatasetUrl(els.root, ["updateProcessDateUrl", "dataUpdateProcessDateUrl", "updateProcessDateURL"]);
}

function getUserGrade() {
  return String(els.root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

function canEditProcessDate() {
  const g = getUserGrade();
  return g === "superuser" || g === "head";
}

/* =========================================================
   Normalizers / Escapes
========================================================= */
function normalizeYM(ym) {
  const s = String(ym || "").trim();
  if (!s) return "";
  if (/^\d{4}-\d{2}$/.test(s)) return s;

  const digits = s.replaceAll("-", "").replaceAll("/", "").replaceAll(".", "");
  if (/^\d{6}$/.test(digits)) return `${digits.slice(0, 4)}-${digits.slice(4, 6)}`;
  if (s.length >= 6) return `${s.slice(0, 4)}-${s.slice(-2)}`;
  return s;
}

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

function squeezeSpaces(s) {
  return String(s || "")
    .replaceAll(">", " ") // 혹시 들어오면 제거
    .replace(/\s+/g, " ")
    .trim();
}

/* =========================================================
   UI helpers
========================================================= */
function revealSections() {
  const inputSec = document.getElementById("inputSection");
  const mainSec = document.getElementById("mainSheet");
  if (inputSec) inputSec.hidden = false;
  if (mainSec) mainSec.hidden = false;

  requestAnimationFrame(() => requestAnimationFrame(() => adjustDT()));
}

function safeResetInput() {
  try {
    resetInputSection();
  } catch (e) {
    console.warn("[rate/fetch] resetInputSection 실패(무시):", e);
  }
}

/* =========================================================
   CSRF
========================================================= */
function getCSRFToken() {
  return window.csrfToken || "";
}

/* =========================================================
   Server calls (process_date)
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
    credentials: "same-origin",
    body: JSON.stringify({
      id,
      process_date: value || "",
      kind: "rate",
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `처리일자 저장 실패 (${res.status})`);
  }
  return data;
}

/* =========================================================
   Render helpers
========================================================= */
function renderAfterCell(val) {
  const v = String(val ?? "").trim();
  if (!v) return "";
  return `<span class="cell-after">${escapeHtml(v)}</span>`;
}

function buildActionButtons(row) {
  // ✅ 삭제는 delete.js(attachDeleteHandlers)가 담당, 여기서는 버튼만 렌더
  const id = String(row.id || "").trim();
  if (!id) return "";
  return `
    <button type="button"
            class="btn btn-sm btn-outline-danger btnDeleteRow"
            data-id="${escapeAttr(id)}">
      삭제
    </button>
  `;
}

function renderProcessDateCell(_value, _type, row) {
  const grade = getUserGrade();
  const val = (row.process_date || "").trim();

  // leader는 보기만
  if (grade === "leader") {
    return `<span>${escapeHtml(val || "")}</span>`;
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

/* =========================================================
   DataTables columns
   ✅ "대상자" 다음에 "소속" 컬럼 추가
========================================================= */
const MAIN_COLUMNS = [
  { data: "rq_display", defaultContent: "", width: "140px" }, // 요청자
  { data: "tg_display", defaultContent: "", width: "140px" }, // 대상자
  { data: "tg_affiliation", defaultContent: "-", width: "220px" }, // 소속

  { data: "before_ftable", defaultContent: "", width: "70px" },
  { data: "before_frate", defaultContent: "", width: "70px" },

  { data: "after_ftable", defaultContent: "", width: "70px", render: (v) => renderAfterCell(v) },
  { data: "after_frate", defaultContent: "", width: "70px" },

  { data: "before_ltable", defaultContent: "", width: "70px" },
  { data: "before_lrate", defaultContent: "", width: "70px" },

  { data: "after_ltable", defaultContent: "", width: "70px", render: (v) => renderAfterCell(v) },
  { data: "after_lrate", defaultContent: "", width: "70px" },

  { data: "memo", defaultContent: "", width: "150px" },

  { data: "request_date", defaultContent: "", width: "120px" },

  {
    data: "process_date",
    width: "120px",
    orderable: false,
    searchable: false,
    render: renderProcessDateCell,
    defaultContent: "",
  },
  {
    data: "id",
    width: "70px",
    orderable: false,
    searchable: false,
    render: (_id, _type, row) => buildActionButtons(row),
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
    mainDT.draw(false);
  } catch (_) {}
}

function destroyIfExists() {
  try {
    if (els.mainTable && window.jQuery?.fn?.DataTable?.isDataTable?.(els.mainTable)) {
      window.jQuery(els.mainTable).DataTable().clear().destroy();
    }
  } catch (_) {}
  mainDT = null;
}

/**
 * ✅ thead <th> 개수와 columns 개수가 다르면 DataTables가 헤더를 망가뜨릴 수 있음.
 * 컬럼 구조 변경/캐시/부분갱신 등에도 안전하게 “강제 재생성” 하도록 체크.
 */
function needRebuildDT() {
  if (!els.mainTable) return false;
  const thCount = els.mainTable.querySelectorAll("thead th").length;
  return thCount && thCount !== MAIN_COLUMNS.length;
}

function ensureMainDT() {
  if (!canUseDataTables()) return null;

  // ✅ 컬럼 mismatch면 무조건 재생성
  if (needRebuildDT()) {
    destroyIfExists();
  }

  if (mainDT) return mainDT;

  destroyIfExists();

  mainDT = window.jQuery(els.mainTable).DataTable({
    paging: true,
    searching: true,
    info: true,
    ordering: false,
    pageLength: 10,
    lengthChange: true,

    autoWidth: false,
    scrollX: false,
    destroy: false,

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

/* =========================================================
   Fallback render (thead와 동일한 컬럼 순서로)
========================================================= */
function renderMainSheetFallback(rows) {
  if (!els.mainTable) return;
  const tbody = els.mainTable.querySelector("tbody");
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
      <td>${escapeHtml(r.rq_display || "")}</td>
      <td>${escapeHtml(r.tg_display || "")}</td>
      <td>${escapeHtml(r.tg_affiliation || "-")}</td>

      <td>${escapeHtml(r.before_ftable || "")}</td>
      <td class="text-center">${escapeHtml(r.before_frate || "")}</td>

      <td>${renderAfterCell(r.after_ftable || "")}</td>
      <td class="text-center">${escapeHtml(r.after_frate || "")}</td>

      <td>${escapeHtml(r.before_ltable || "")}</td>
      <td class="text-center">${escapeHtml(r.before_lrate || "")}</td>

      <td>${renderAfterCell(r.after_ltable || "")}</td>
      <td class="text-center">${escapeHtml(r.after_lrate || "")}</td>

      <td>${escapeHtml(r.memo || "")}</td>

      <td class="text-center">${escapeHtml(r.request_date || "")}</td>

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

function renderMainSheet(rows) {
  const dt = ensureMainDT();
  if (dt) {
    dt.clear();
    if (rows?.length) dt.rows.add(rows);
    dt.draw();
    requestAnimationFrame(() => adjustDT());
    return;
  }
  renderMainSheetFallback(rows);
}

/* =========================================================
   Delegation + Resize (once)
========================================================= */
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
      alertBox(err?.message || "처리일자 저장 실패");
    } finally {
      hideLoading();
    }
  });
}

function bindResizeOnce() {
  if (resizeBound) return;
  resizeBound = true;

  window.addEventListener(
    "resize",
    () => requestAnimationFrame(() => adjustDT()),
    { passive: true }
  );
}

/* =========================================================
   Normalize row
========================================================= */
function formatNameId(name, id) {
  const n = String(name || "").trim();
  const i = String(id || "").trim();
  if (!n && !i) return "";
  if (!i) return n;
  if (!n) return `(${i})`;
  return `${n}(${i})`;
}

function joinTeams(a, b, c) {
  const arr = [a, b, c]
    .map((x) => String(x ?? "").trim())
    .filter((x) => x && x !== "-");
  // ✅ 요청사항: "팀A 팀B 팀C" (구분자 공백)
  return arr.length ? arr.join(" ") : "-";
}

function normalizeRateRow(row = {}) {
  const requester_name = row.requester_name || row.rq_name || "";
  const requester_id = row.requester_id || row.rq_id || "";

  const target_name = row.target_name || row.tg_name || "";
  const target_id = row.target_id || row.tg_id || "";

  // ✅ 서버 호환 키: tg_affiliation / target_affiliation / (팀A/B/C)
  const rawAff =
    String(row.tg_affiliation || row.target_affiliation || "").trim() ||
    joinTeams(row.tg_team_a, row.tg_team_b, row.tg_team_c);

  const tgAff = squeezeSpaces(rawAff) || "-";

  return {
    id: row.id || "",

    rq_display: formatNameId(requester_name, requester_id),
    tg_display: formatNameId(target_name, target_id),

    tg_affiliation: tgAff,

    before_ftable: row.before_ftable || "",
    before_frate: row.before_frate || "",

    after_ftable: row.after_ftable || "",
    after_frate: row.after_frate || "",

    before_ltable: row.before_ltable || "",
    before_lrate: row.before_lrate || "",

    after_ltable: row.after_ltable || "",
    after_lrate: row.after_lrate || "",

    memo: row.memo || "",

    request_date: row.request_date || row.created_date || row.created_at || "",
    process_date: row.process_date || "",
  };
}

/* =========================================================
   Fetch
========================================================= */
export async function fetchData(payload = {}) {
  if (!els.root) return;

  // ✅ 삭제 후 재조회 등에 사용 (delete.js에서 활용)
  window.__lastRateFetchPayload = payload;

  bindDelegationOnce();
  bindResizeOnce();

  const baseUrl = getFetchBaseUrl();
  if (!baseUrl) {
    console.warn("[rate/fetch] fetchUrl 누락", els.root?.dataset);
    revealSections();
    safeResetInput();
    renderMainSheet([]);
    return;
  }

  const ym = normalizeYM(payload.ym);
  const branch = String(payload.branch || "").trim();

  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("month", ym);
  url.searchParams.set("branch", branch);

  showLoading("데이터를 불러오는 중입니다...");
  try {
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const data = await res.json().catch(() => ({}));
    const rawRows = Array.isArray(data?.rows) ? data.rows : [];

    revealSections();

    if (data.status !== "success") {
      safeResetInput();
      renderMainSheet([]);
      return;
    }

    const rows = rawRows.map(normalizeRateRow);
    safeResetInput();
    renderMainSheet(rows);

    setTimeout(() => adjustDT(), 0);
  } catch (err) {
    console.error("❌ [rate/fetch] 예외:", err);
    revealSections();
    safeResetInput();
    renderMainSheet([]);
  } finally {
    hideLoading();
  }
}
