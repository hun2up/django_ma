// django_ma/static/js/partner/manage_efficiency/fetch.js
// ======================================================
// 📘 지점효율 페이지 - 조회(fetch) 틀 (스캐폴딩)
// - dataset 기반 fetch URL 사용
// - DataTables 있으면 사용, 없으면 fallback
// - normalize/columns는 이후 지표 확정 시 확장
// ======================================================

import { els } from "./dom_refs.js";

import { getDatasetUrl } from "../../common/manage/dataset.js";
import { normalizeYM } from "../../common/manage/ym.js";
import { escapeHtml, escapeAttr } from "../../common/manage/escape.js";
import { showLoading, hideLoading } from "../../common/manage/loading.js";
import { canUseDataTables, destroyDataTableIfExists, safeAdjust } from "../../common/manage/datatables.js";

let mainDT = null;

/* ============================================================
   Dataset URL
============================================================ */
function getFetchBaseUrl() {
  // ✅ 템플릿에서 data-fetch-url 혹은 data-eff-fetch-url 등으로 줄 수 있음
  return getDatasetUrl(els.root, [
    "fetchUrl",
    "dataFetchUrl",
    "effFetchUrl",
    "dataEffFetchUrl",
    "fetchURL",
    "dataFetchURL",
  ]);
}

/* ============================================================
   섹션 표시 (편제/요율 스타일 맞춤)
============================================================ */
function revealSections() {
  const mainSec = document.getElementById("mainSheet") || document.getElementById("mainSection");
  if (mainSec) mainSec.hidden = false;

  requestAnimationFrame(() => requestAnimationFrame(() => adjustDT()));
}

/* ============================================================
   DataTables columns (스캐폴딩)
   - 실제 지점효율 지표 확정되면 이 부분만 교체/확장하면 됨
============================================================ */
const MAIN_COLUMNS = [
  { title: "지점", data: "branch", defaultContent: "" },
  { title: "월도", data: "ym", defaultContent: "" },
  { title: "지표", data: "metric", defaultContent: "" },
  { title: "값", data: "value", defaultContent: "" },
];

const MAIN_COLSPAN = MAIN_COLUMNS.length;

function adjustDT() {
  if (!mainDT) return;
  safeAdjust(mainDT);
}

function ensureMainDT() {
  if (!canUseDataTables(els.mainTable)) return null;
  if (mainDT) return mainDT;

  destroyDataTableIfExists(els.mainTable);

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
    columns: MAIN_COLUMNS.map((c) => ({
      data: c.data,
      defaultContent: c.defaultContent ?? "",
    })),
  });

  return mainDT;
}

/* ============================================================
   Fallback render
============================================================ */
function renderFallback(rows) {
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

  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(r.branch)}</td>
      <td class="text-center">${escapeHtml(r.ym)}</td>
      <td>${escapeHtml(r.metric)}</td>
      <td class="text-end">${escapeHtml(r.value)}</td>
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
    requestAnimationFrame(() => adjustDT());
    return;
  }
  renderFallback(rows);
}

/* ============================================================
   Normalize row (스캐폴딩)
============================================================ */
function normalizeRow(row = {}, ym = "") {
  // 서버 구조 확정 전이므로 최소 안전 변환만 제공
  return {
    branch: row.branch || row.branch_name || "",
    ym: row.ym || row.month || ym,
    metric: row.metric || row.name || row.label || "",
    value: row.value ?? row.amount ?? row.score ?? "",
  };
}

/* ============================================================
   Fetch public API
   payload: { ym, branch, grade, ... } 형태로 확장 가능
============================================================ */
export async function fetchData(payload = {}) {
  if (!els.root) return;

  const baseUrl = getFetchBaseUrl();
  if (!baseUrl) {
    console.warn("[efficiency/fetch] fetchUrl 누락", els.root?.dataset);
    revealSections();
    renderMain([]);
    return;
  }

  const ym = normalizeYM(payload.ym);
  const branch = String(payload.branch || "").trim();

  const url = new URL(baseUrl, window.location.origin);
  if (ym) url.searchParams.set("month", ym);
  if (branch) url.searchParams.set("branch", branch);

  showLoading("데이터를 불러오는 중입니다...");

  try {
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const data = await res.json().catch(() => ({}));
    const rawRows = Array.isArray(data?.rows) ? data.rows : Array.isArray(data?.data) ? data.data : [];

    revealSections();

    if (data.status && data.status !== "success") {
      renderMain([]);
      return;
    }

    const rows = rawRows.map((r) => normalizeRow(r, ym));
    renderMain(rows);
  } catch (err) {
    console.error("❌ [efficiency/fetch] 예외:", err);
    revealSections();
    renderMain([]);
  } finally {
    hideLoading();
  }
}
