// django_ma/static/js/partner/manage_structure/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, pad2 } from "./utils.js";
import { attachDeleteHandlers } from "./delete.js";

let isFetching = false;

// ------------------------------------------------------------
// helpers
// ------------------------------------------------------------
function canEditProcessDate() {
  const g = window.currentUser?.grade || "";
  return ["superuser", "main_admin"].includes(g);
}

function buildYM(ym) {
  const y = ym ? ym.split("-")[0] : els.year?.value;
  const m = ym ? ym.split("-")[1] : els.month?.value;
  return `${y}-${pad2(m)}`;
}

function buildFetchUrl(ymValue, branchValue, meta = {}) {
  const { grade, level, team_a, team_b, team_c } = meta || {};
  const params = new URLSearchParams({
    month: ymValue,
    branch: branchValue || "",
    grade: grade || "",
    level: level || "",
    team_a: team_a || "",
    team_b: team_b || "",
    team_c: team_c || "",
  });

  const base = els.root?.dataset?.dataFetchUrl;
  if (!base) throw new Error("dataFetchUrl 누락");
  return `${base}?${params.toString()}`;
}

async function safeParseJson(res) {
  const text = await res.text();
  console.log("📦 Raw Response:", text);

  try {
    return JSON.parse(text);
  } catch {
    throw new Error("서버 응답 파싱 실패");
  }
}

async function destroyDataTableIfExists() {
  if (!window.jQuery || !window.jQuery.fn?.DataTable) return;
  if (!window.jQuery.fn.DataTable.isDataTable("#mainTable")) return;

  $("#mainTable").DataTable().clear().destroy();
  // DOM 정리 시간 확보
  await new Promise((r) => setTimeout(r, 20));
}

function initDataTable() {
  if (!window.jQuery || !window.jQuery.fn?.DataTable) return;

  try {
    $("#mainTable").DataTable({
      language: {
        emptyTable: "데이터가 없습니다.",
        search: "검색:",
        lengthMenu: "_MENU_개씩 보기",
        info: "_TOTAL_건 중 _START_–_END_ 표시",
        infoEmpty: "0건",
        paginate: { previous: "이전", next: "다음" },
      },
      order: [],
      autoWidth: false,
      pageLength: 10,
      destroy: true,
    });
  } catch (e) {
    console.warn("⚠️ DataTable 초기화 중 오류:", e);
  }
}

function rowHtml(r) {
  const isAdmin = ["superuser", "main_admin"].includes(window.currentUser?.grade || "");

  // ✅ 처리일자: 관리자만 입력 가능
  const processDateCell = canEditProcessDate()
    ? `<input type="date"
        class="form-control form-control-sm processDateInput"
        data-id="${r.id}"
        value="${r.process_date || ""}"
      />`
    : `${r.process_date || ""}`;

  return `
    <tr data-id="${r.id}">
      <td>${r.requester_name || ""}</td>
      <td>${r.requester_id || ""}</td>
      <td>${r.requester_branch || ""}</td>
      <td>${r.target_name || ""}</td>
      <td>${r.target_id || ""}</td>
      <td>${r.target_branch || ""}</td>
      <td>${r.chg_branch || ""}</td>
      <td>${r.rank || ""}</td>
      <td>${r.chg_rank || ""}</td>
      <td>${r.or_flag ? "✅" : ""}</td>
      <td>${r.memo || ""}</td>
      <td>${r.request_date || ""}</td>
      <td>${processDateCell}</td>
      <td>
        ${
          isAdmin
            ? `<button class="btn btn-sm btn-outline-danger btnDeleteRow" data-id="${r.id}">삭제</button>`
            : ""
        }
      </td>
    </tr>
  `;
}

function renderEmpty(tbody) {
  tbody.innerHTML = `<tr><td colspan="14" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
}

// ------------------------------------------------------------
// public
// ------------------------------------------------------------
export async function fetchData(ym = null, branchValue = null, meta = {}) {
  if (isFetching) {
    console.warn("⚠️ fetchData 중복 호출 방지됨");
    return;
  }
  isFetching = true;

  const ymValue = buildYM(ym);
  const b = branchValue ?? els.branch?.value ?? "";

  console.log("🚀 fetchData() 실행:", { ymValue, branch: b, meta });

  showLoading("데이터 불러오는 중...");

  try {
    const url = buildFetchUrl(ymValue, b, meta);
    console.log("📡 Fetch 요청 URL:", url);

    const res = await fetch(url);
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const data = await safeParseJson(res);
    if (data.status !== "success") throw new Error(data.message || "조회 실패");

    const rows = Array.isArray(data.rows) ? data.rows : [];
    await renderMainTable(rows);
    console.log(`✅ 데이터 로드 완료: ${rows.length}건`);
  } catch (err) {
    console.error("❌ fetchData 에러:", err);
    alertBox("데이터를 불러오지 못했습니다.");
    await renderMainTable([]); // 안전 초기화
  } finally {
    hideLoading();
    isFetching = false;
  }
}

export async function renderMainTable(rows = []) {
  const tbody = els.mainTable?.querySelector("tbody");
  if (!tbody) return;

  // ✅ DataTable 정리
  await destroyDataTableIfExists();

  // ✅ 초기화
  tbody.innerHTML = "";

  if (!rows.length) {
    console.log("ℹ️ 조회 결과 없음 — DataTable 미초기화");
    renderEmpty(tbody);
    return;
  }

  // ✅ 렌더
  tbody.insertAdjacentHTML("beforeend", rows.map(rowHtml).join(""));

  // ✅ DataTable/삭제/처리일자 핸들러
  initDataTable();
  attachDeleteHandlers();
  attachProcessDateHandlers();

  console.log("✅ 메인시트 렌더링 완료");
}

// ------------------------------------------------------------
// 처리일자 수정(관리자만)
// - 이벤트 위임으로 DataTables redraw에도 안정
// ------------------------------------------------------------
let processDateHandlerBound = false;

function attachProcessDateHandlers() {
  if (processDateHandlerBound) return;
  processDateHandlerBound = true;

  document.addEventListener("change", async (e) => {
    const input = e.target;
    if (!input.classList.contains("processDateInput")) return;

    if (!canEditProcessDate()) return;

    const id = input.dataset.id;
    const process_date = input.value; // YYYY-MM-DD
    const url = els.root?.dataset?.updateProcessDateUrl;

    if (!url) {
      console.warn("⚠️ updateProcessDateUrl 누락");
      return;
    }
    if (!id) return;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": window.csrfToken,
        },
        body: JSON.stringify({ id, process_date }),
      });

      const data = await res.json();
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "처리일자 저장 실패");
      }

      input.classList.add("is-valid");
      setTimeout(() => input.classList.remove("is-valid"), 900);
    } catch (err) {
      console.error("❌ 처리일자 저장 오류:", err);
      input.classList.add("is-invalid");
      setTimeout(() => input.classList.remove("is-invalid"), 1200);
      alertBox("처리일자 저장 중 오류가 발생했습니다.");
    }
  });
}
