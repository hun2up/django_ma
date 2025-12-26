// django_ma/static/js/partner/manage_rate/index.js
import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2, alertBox } from "./utils.js";
import { initInputRowEvents } from "./input_rows.js";

const AUTOLOAD_GRADES = new Set(["main_admin", "sub_admin"]);

/* ==========================
   dataset helpers
========================== */
function ds(key, fallback = "") {
  return (els.root?.dataset?.[key] ?? fallback).toString().trim();
}

function getGrade() {
  return ds("userGrade", window.currentUser?.grade || "");
}

function getDefaultBranch() {
  return ds("defaultBranch", window.currentUser?.branch || "");
}

function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") return (els.branchSelect?.value || "").trim();
  return getDefaultBranch();
}

function getYMFromSelectors() {
  const y = (els.yearSelect?.value || "").trim();
  const m = (els.monthSelect?.value || "").trim();
  if (!y || !m) return "";
  return `${y}-${pad2(m)}`;
}

function buildFetchPayload(ym) {
  return {
    ym,
    branch: getEffectiveBranch(),
    grade: getGrade(),
    level: ds("userLevel"),
    team_a: ds("teamA"),
    team_b: ds("teamB"),
    team_c: ds("teamC"),
  };
}

/* ==========================
   requester autofill
========================== */
function fillRequesterRow(row) {
  const u = window.currentUser || {};
  const set = (name, val) => {
    const el = row?.querySelector?.(`[name="${name}"]`);
    if (el) el.value = val ?? "";
  };
  set("rq_name", u.name || "");
  set("rq_id", u.id || "");
}

function fillRequesterAllRows() {
  document
    .querySelectorAll("#inputTable tbody tr.input-row")
    .forEach((row) => fillRequesterRow(row));
}

/* ==========================
   period dropdown
========================== */
function fillDropdown(el, start, end, selected, suffix) {
  if (!el) return;
  el.innerHTML = "";
  for (let v = start; v <= end; v++) {
    const opt = document.createElement("option");
    opt.value = String(v);
    opt.textContent = `${v}${suffix}`;
    el.appendChild(opt);
  }
  el.value = String(selected);
}

function initPeriodDropdowns() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  fillDropdown(els.yearSelect, y - 1, y + 1, y, "년");
  fillDropdown(els.monthSelect, 1, 12, m, "월");
}

/* ==========================
   search
========================== */
async function runSearch({ ym, branch } = {}) {
  const finalYM = ym || getYMFromSelectors();
  const finalBranch = branch || getEffectiveBranch();

  if (!finalYM || !finalBranch) {
    alertBox("연도·월도 및 지점을 선택해주세요.");
    return;
  }

  try {
    await fetchData(buildFetchPayload(finalYM));
  } catch (err) {
    console.error("❌ [fetchData] 실패:", err);
    alertBox("데이터 조회 중 오류가 발생했습니다.");
  }
}

function initSearchButton() {
  if (!els.btnSearch) return;
  els.btnSearch.addEventListener("click", () => runSearch());
}

/* ==========================
   superuser part/branch loader
========================== */
function initSuperuserPartsBranches() {
  if (getGrade() !== "superuser") return;
  if (typeof window.loadPartsAndBranches !== "function") return;
  window.loadPartsAndBranches("manage-rate");
}

/* ==========================
   table check modal
========================== */
function getTableFetchUrl(branch) {
  const base = ds("tableFetchUrl"); // data-table-fetch-url
  if (!base) return "";
  const url = new URL(base, window.location.origin);
  url.searchParams.set("branch", branch);
  return url.toString();
}

function escapeAttr(v) {
  return String(v ?? "").replaceAll('"', "&quot;");
}

function renderTableCheckHTML(rows) {
  const tbody = rows
    .map((r) => {
      const t = r.table || r.table_name || "-";
      const rate = r.rate ?? "-";
      return `
        <tr>
          <td class="text-truncate" title="${escapeAttr(t)}">${t}</td>
          <td class="text-center">${rate}</td>
        </tr>`;
    })
    .join("");

  return `
    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
      <table class="table table-sm table-bordered align-middle mb-0"
             style="font-size: 0.9rem; table-layout: fixed; width: 100%; text-align: center;">
        <colgroup>
          <col style="width: 70%;">
          <col style="width: 30%;">
        </colgroup>
        <thead class="table-light">
          <tr>
            <th class="text-center">테이블명</th>
            <th class="text-center">요율(%)</th>
          </tr>
        </thead>
        <tbody>${tbody}</tbody>
      </table>
    </div>`;
}

function initTableCheckModal() {
  const btnCheck = document.getElementById("btnCheckTable");
  const modalBody = document.getElementById("tableCheckBody");
  const modalEl = document.getElementById("tableCheckModal");
  if (!btnCheck || !modalBody || !modalEl) return;

  btnCheck.addEventListener("click", async () => {
    const branch = getEffectiveBranch();
    if (!branch) return alertBox("지점 정보가 없습니다. 부서/지점을 먼저 선택하세요.");

    const url = getTableFetchUrl(branch);
    if (!url) return alertBox("테이블 조회 URL이 없습니다. (data-table-fetch-url 확인)");

    modalBody.innerHTML = `<div class="py-4 text-muted">불러오는 중...</div>`;
    new bootstrap.Modal(modalEl).show();

    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
      if (data.status !== "success") throw new Error(data.message || "조회 실패");

      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        modalBody.innerHTML = `<div class="py-4 text-muted">등록된 테이블이 없습니다.</div>`;
        return;
      }
      modalBody.innerHTML = renderTableCheckHTML(rows);
    } catch (err) {
      console.error("❌ [테이블 확인] 실패:", err);
      modalBody.innerHTML = `<div class="py-4 text-danger">테이블 정보를 불러오지 못했습니다.</div>`;
    }
  });
}

/* ==========================
   autoload
========================== */
function initAutoLoad() {
  const grade = getGrade();
  if (!AUTOLOAD_GRADES.has(grade)) return;

  const now = new Date();
  const ym = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
  const branch = getEffectiveBranch();
  if (!branch) return;

  // manage_boot.js와 충돌 방지: 아주 짧게만 지연
  setTimeout(() => runSearch({ ym, branch }), 250);
}

/* ==========================
   init
========================== */
function init() {
  if (!els.root) return;

  initPeriodDropdowns();
  initInputRowEvents();
  fillRequesterAllRows();

  initSuperuserPartsBranches();
  initSearchButton();
  initAutoLoad();
  initTableCheckModal();
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    init();
  } catch (err) {
    console.error("❌ [manage_rate/index.js 초기화 오류]", err);
  }
});

export { fillRequesterRow, fillRequesterAllRows, runSearch };
