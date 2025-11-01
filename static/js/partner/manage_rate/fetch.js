// django_ma/static/js/partner/manage_rate/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading } from "./utils.js";

let mainDT = null;

/**
 * ✅ DataTables 초기화 (1회)
 */
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

/**
 * ✅ 서버에서 데이터 받아오기
 * payload = { ym, branch, grade, level, team_a, team_b, team_c }
 */
export async function fetchData(payload = {}) {
  if (!els.root) return;

  const baseUrl = els.root.dataset.dataFetchUrl;
  if (!baseUrl) {
    console.warn("[rate/fetch] data-fetch-url 이 없습니다.");
    return;
  }

  // 🔹 month 파라미터 안전 보정 (YYYY-MM)
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
    const data = await res.json();

    if (!data || data.status !== "success") {
      console.warn("[rate/fetch] success 아님, 빈 상태로 렌더");
      renderInputSection([]);
      renderMainSheet([]);
      return;
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    renderInputSection(rows);
    renderMainSheet(rows);
  } catch (err) {
    console.error("[rate/fetch] 에러 발생", err);
    renderInputSection([]);
    renderMainSheet([]);
  } finally {
    hideLoading();
  }
}

/**
 * ✅ 내용입력 카드 렌더링
 */
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

/**
 * ✅ 메인 시트 렌더링
 */
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

  // 백업 모드
  if (!els.mainTable) return;
  const tbody = els.mainTable.querySelector("tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.textContent = "데이터가 없습니다.";
    td.colSpan = 12;
    tr.appendChild(td);
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

/**
 * ✅ 서버 응답 → 표준형 필드 정규화
 */
function normalizeRateRow(row = {}) {
  return {
    id: row.id || row.pk || "",
    requester_name: row.requester_name || row.req_name || row.rq_name || "",
    requester_id: row.requester_id || row.req_empno || row.rq_id || "",
    requester_branch: row.requester_branch || row.req_branch || row.rq_branch || "",
    target_name: row.target_name || row.tg_name || "",
    target_id: row.target_id || row.tg_id || "",
    table_before: row.table_before || row.before_table || row.before_branch || "",
    table_after: row.table_after || row.after_table || row.after_branch || "",
    rate_before: row.rate_before || row.before_rate || row.before_rank || "",
    rate_after: row.rate_after || row.after_rate || row.after_rank || "",
    memo: row.memo || "",
    process_date: row.process_date || row.proc_date || "",
  };
}

/**
 * ✅ 빈 입력 행
 */
function createEmptyInputRow() {
  const tr = document.createElement("tr");
  tr.classList.add("input-row");
  tr.innerHTML = `
    <td><input type="text" name="rq_name" class="form-control form-control-sm" placeholder="요청자"></td>
    <td><input type="text" name="rq_id" class="form-control form-control-sm" placeholder="사번"></td>
    <td><input type="text" name="rq_branch" class="form-control form-control-sm" placeholder="소속"></td>
    <td><input type="text" name="tg_name" class="form-control form-control-sm" placeholder="대상자"></td>
    <td><input type="text" name="tg_id" class="form-control form-control-sm" placeholder="사번"></td>
    <td><input type="text" name="table_before" class="form-control form-control-sm" placeholder="변경전 테이블"></td>
    <td><input type="text" name="table_after" class="form-control form-control-sm" placeholder="변경후 테이블"></td>
    <td><input type="text" name="rate_before" class="form-control form-control-sm" placeholder="변경전 요율"></td>
    <td><input type="text" name="rate_after" class="form-control form-control-sm" placeholder="변경후 요율"></td>
    <td><input type="text" name="memo" class="form-control form-control-sm" placeholder="메모"></td>
  `;
  return tr;
}

function createInputRowFromData(row) {
  const r = normalizeRateRow(row);
  const tr = document.createElement("tr");
  tr.classList.add("input-row");
  tr.innerHTML = `
    <td><input type="text" name="rq_name" class="form-control form-control-sm" value="${r.requester_name || ""}"></td>
    <td><input type="text" name="rq_id" class="form-control form-control-sm" value="${r.requester_id || ""}"></td>
    <td><input type="text" name="rq_branch" class="form-control form-control-sm" value="${r.requester_branch || ""}"></td>
    <td><input type="text" name="tg_name" class="form-control form-control-sm" value="${r.target_name || ""}"></td>
    <td><input type="text" name="tg_id" class="form-control form-control-sm" value="${r.target_id || ""}"></td>
    <td><input type="text" name="table_before" class="form-control form-control-sm" value="${r.table_before || ""}"></td>
    <td><input type="text" name="table_after" class="form-control form-control-sm" value="${r.table_after || ""}"></td>
    <td><input type="text" name="rate_before" class="form-control form-control-sm" value="${r.rate_before || ""}"></td>
    <td><input type="text" name="rate_after" class="form-control form-control-sm" value="${r.rate_after || ""}"></td>
    <td><input type="text" name="memo" class="form-control form-control-sm" value="${r.memo || ""}"></td>
  `;
  return tr;
}

/**
 * ✅ 액션 버튼 생성
 */
function buildActionButtons(row) {
  return `
    <button type="button" class="btn btn-sm btn-outline-danger btnDeleteRow" data-id="${row.id || ""}">
      삭제
    </button>
  `;
}
