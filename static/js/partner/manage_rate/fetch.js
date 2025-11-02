// django_ma/static/js/partner/manage_rate/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading } from "./utils.js";

let mainDT = null;

/* ============================================================
   ✅ DataTables 초기화 (1회)
============================================================ */
function ensureMainDT() {
  if (!els.mainTable) return null;
  if (!window.jQuery || !window.jQuery.fn?.DataTable) return null;
  if (mainDT) return mainDT;

  mainDT = window.jQuery(els.mainTable).DataTable({
    paging: false,
    searching: false,
    info: false,
    ordering: false,
    destroy: true,
    language: { emptyTable: "데이터가 없습니다." },
  });
  return mainDT;
}

/* ============================================================
   ✅ 서버 데이터 조회
   payload = { ym, branch, grade, level, team_a, team_b, team_c }
============================================================ */
export async function fetchData(payload = {}) {
  if (!els.root) return;

  const baseUrl = els.root.dataset.dataFetchUrl;
  if (!baseUrl) {
    console.warn("[rate/fetch] ⚠️ data-fetch-url 누락");
    return;
  }

  // 🔹 month 파라미터 보정 (YYYY-MM)
  let ym = (payload.ym || "").trim();
  if (ym && !/^\d{4}-\d{2}$/.test(ym)) {
    const y = ym.slice(0, 4);
    const m = ym.slice(-2);
    ym = `${y}-${m}`;
  }

  // 🔹 URL 생성
  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("month", ym);
  url.searchParams.set("branch", payload.branch || "");
  url.searchParams.set("grade", payload.grade || "");
  url.searchParams.set("level", payload.level || "");
  url.searchParams.set("team_a", payload.team_a || "");
  url.searchParams.set("team_b", payload.team_b || "");
  url.searchParams.set("team_c", payload.team_c || "");

  console.log("➡️ [rate/fetch] FETCH 호출:", url.toString());

  showLoading("데이터를 불러오는 중입니다...");

  try {
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const data = await res.json();
    const rows = Array.isArray(data?.rows) ? data.rows : [];

    if (data.status !== "success") {
      console.warn("[rate/fetch] ⚠️ 서버 응답 status != success", data);
      renderInputSection([]);
      renderMainSheet([]);
      revealSections();
      hideLoading();
      return;
    }

    console.log(`✅ [rate/fetch] ${rows.length}건 수신 완료`);
    renderInputSection(rows);
    renderMainSheet(rows);
  } catch (err) {
    console.error("❌ [rate/fetch] 예외 발생:", err);
    renderInputSection([]);
    renderMainSheet([]);
  } finally {
    revealSections();
    hideLoading();
  }
}

/* ============================================================
   ✅ UI 표시 제어 (항상 노출 보장)
============================================================ */
function revealSections() {
  const inputSec = document.getElementById("inputSection");
  const mainSec = document.getElementById("mainSheet");
  if (inputSec) inputSec.hidden = false;
  if (mainSec) mainSec.hidden = false;
}

/* ============================================================
   ✅ 내용입력 렌더링
============================================================ */
function renderInputSection(rows) {
  if (!els.inputTable) return;
  const tbody = els.inputTable.querySelector("tbody");
  if (!tbody) return;

  tbody.innerHTML = "";
  if (!rows.length) {
    tbody.appendChild(createEmptyInputRow());
    return;
  }

  rows.forEach((row) => tbody.appendChild(createInputRowFromData(row)));
}

/* ============================================================
   ✅ 메인시트 렌더링
============================================================ */
function renderMainSheet(rows) {
  const dt = ensureMainDT();
  if (dt) {
    dt.clear();
    if (rows.length) {
      const mapped = rows.map(normalizeRateRow).map((r) => [
        r.requester_name,
        r.requester_id,
        r.requester_branch,
        r.target_name,
        r.target_id,
        r.table_before,
        r.table_after,
        r.rate_before,
        r.rate_after,
        r.memo,
        r.process_date,
        buildActionButtons(r),
      ]);
      dt.rows.add(mapped).draw();
    } else {
      dt.draw();
    }
    return;
  }

  // ⚙️ fallback: DataTables 미사용 시 수동 렌더링
  if (!els.mainTable) return;
  const tbody = els.mainTable.querySelector("tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="12" class="text-center text-muted">데이터가 없습니다.</td>`;
    tbody.appendChild(tr);
    return;
  }

  rows.map(normalizeRateRow).forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.requester_name}</td>
      <td>${r.requester_id}</td>
      <td>${r.requester_branch}</td>
      <td>${r.target_name}</td>
      <td>${r.target_id}</td>
      <td>${r.table_before}</td>
      <td>${r.table_after}</td>
      <td>${r.rate_before}</td>
      <td>${r.rate_after}</td>
      <td>${r.memo}</td>
      <td>${r.process_date}</td>
      <td>${buildActionButtons(r)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ============================================================
   ✅ 데이터 정규화
============================================================ */
function normalizeRateRow(row = {}) {
  return {
    id: row.id || "",
    requester_name: row.requester_name || row.rq_name || "",
    requester_id: row.requester_id || row.rq_id || "",
    target_name: row.target_name || row.tg_name || "",
    target_id: row.target_id || row.tg_id || "",
    before_ftable: row.before_ftable || "",
    before_frate: row.before_frate || "",
    after_ftable: row.after_ftable || "",
    after_frate: row.after_frate || "",
    before_ltable: row.before_ltable || "",
    before_lrate: row.before_lrate || "",    
    after_ltable: row.after_ltable || "",
    after_lrate: row.after_lrate || "",
    memo: row.memo || "",
    process_date: row.process_date || "",
  };
}


/* ============================================================
   ✅ 입력행 생성 (템플릿 구조와 완벽히 일치 — 15열)
============================================================ */
function createEmptyInputRow() {
  const tr = document.createElement("tr");
  tr.classList.add("input-row");
  tr.innerHTML = `
    <td><input type="text" name="rq_name" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="rq_id" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="tg_name" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="tg_id" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="before_ftable" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="before_frate" class="form-control form-control-sm readonly-field text-center" readonly></td>
    <td><input type="text" name="after_ftable" class="form-control form-control-sm"></td>
    <td><input type="text" name="after_frate" class="form-control form-control-sm readonly-field text-center" readonly></td>
    <td><input type="text" name="before_ltable" class="form-control form-control-sm readonly-field" readonly></td>
    <td><input type="text" name="before_lrate" class="form-control form-control-sm readonly-field text-center" readonly></td>    
    <td><input type="text" name="after_ltable" class="form-control form-control-sm"></td>
    <td><input type="text" name="after_lrate" class="form-control form-control-sm readonly-field text-center" readonly></td>
    <td><input type="text" name="memo" class="form-control form-control-sm" placeholder="상세하게 기재"></td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-primary btn-sm btnOpenSearch"
              data-bs-toggle="modal" data-bs-target="#searchUserModal">검색</button>
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-danger btn-sm btnRemoveRow">삭제</button>
    </td>
  `;
  return tr;
}


/* ============================================================
   ✅ 데이터 기반 입력행 생성 (15열 일치)
============================================================ */
function createInputRowFromData(row) {
  const r = normalizeRateRow(row);
  const tr = document.createElement("tr");
  tr.classList.add("input-row");
  tr.innerHTML = `
    <td><input type="text" name="rq_name" class="form-control form-control-sm readonly-field" value="${r.requester_name || ""}" readonly></td>
    <td><input type="text" name="rq_id" class="form-control form-control-sm readonly-field" value="${r.requester_id || ""}" readonly></td>
    <td><input type="text" name="tg_name" class="form-control form-control-sm readonly-field" value="${r.target_name || ""}" readonly></td>
    <td><input type="text" name="tg_id" class="form-control form-control-sm readonly-field" value="${r.target_id || ""}" readonly></td>
    <td><input type="text" name="before_ftable" class="form-control form-control-sm readonly-field" value="${r.before_ftable || ""}" readonly></td>
    <td><input type="text" name="before_frate" class="form-control form-control-sm readonly-field text-center" value="${r.before_frate || ""}" readonly></td>
    <td><input type="text" name="after_ftable" class="form-control form-control-sm" value="${r.after_ftable || ""}"></td>
    <td><input type="text" name="after_frate" class="form-control form-control-sm readonly-field text-center" value="${r.after_frate || ""}" readonly></td>
    <td><input type="text" name="before_ltable" class="form-control form-control-sm readonly-field" value="${r.before_ltable || ""}" readonly></td>
    <td><input type="text" name="before_lrate" class="form-control form-control-sm readonly-field text-center" value="${r.before_lrate || ""}" readonly></td>
        <td><input type="text" name="after_ltable" class="form-control form-control-sm" value="${r.after_ltable || ""}"></td>
    <td><input type="text" name="after_lrate" class="form-control form-control-sm readonly-field text-center" value="${r.after_lrate || ""}" readonly></td>
    <td><input type="text" name="memo" class="form-control form-control-sm" value="${r.memo || ""}" placeholder="상세하게 기재"></td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-primary btn-sm btnOpenSearch"
              data-bs-toggle="modal" data-bs-target="#searchUserModal">검색</button>
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-danger btn-sm btnRemoveRow">삭제</button>
    </td>
  `;
  return tr;
}


/* ============================================================
   ✅ 액션 버튼
============================================================ */
function buildActionButtons(row) {
  return `
    <button type="button" class="btn btn-sm btn-outline-danger btnDeleteRow" data-id="${row.id || ""}">
      삭제
    </button>
  `;
}
