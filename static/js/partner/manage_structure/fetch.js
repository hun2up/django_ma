// django_ma/static/js/partner/manage_structure/fetch.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, pad2 } from "./utils.js";
import { attachDeleteHandlers } from "./delete.js";

let isFetching = false; // ✅ 중복 요청 방지용 플래그

/**
 * ✅ 데이터 조회 및 렌더링 (최종 안정화 버전)
 */
export async function fetchData(ym = null, branchValue = null, meta = {}) {
  if (isFetching) {
    console.warn("⚠️ fetchData 중복 호출 방지됨");
    return;
  }
  isFetching = true;

  const y = ym ? ym.split("-")[0] : els.year?.value;
  const m = ym ? ym.split("-")[1] : els.month?.value;
  const b = branchValue ?? els.branch?.value ?? "";
  const ymValue = `${y}-${pad2(m)}`;

  const { grade, level, team_a, team_b, team_c } = meta || {};

  console.log("🚀 fetchData() 실행:", {
    ymValue,
    branch: b,
    grade,
    level,
    team_a,
    team_b,
    team_c,
  });

  showLoading("데이터 불러오는 중...");

  try {
    const params = new URLSearchParams({
      month: ymValue,
      branch: b,
      grade: grade || "",
      level: level || "",
      team_a: team_a || "",
      team_b: team_b || "",
      team_c: team_c || "",
    });

    const url = `${els.root.dataset.dataFetchUrl}?${params.toString()}`;
    console.log("📡 Fetch 요청 URL:", url);

    const res = await fetch(url);
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const text = await res.text();
    console.log("📦 Raw Response:", text);

    let data = {};
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("서버 응답 파싱 실패");
    }

    if (data.status !== "success") {
      throw new Error(data.message || "조회 실패");
    }

    // ✅ 응답 방어
    const rows = Array.isArray(data.rows) ? data.rows : [];
    renderMainTable(rows);
    console.log(`✅ 데이터 로드 완료: ${rows.length}건`);
  } catch (err) {
    console.error("❌ fetchData 에러:", err);
    alertBox("데이터를 불러오지 못했습니다.");
    renderMainTable([]); // 안전 초기화
  } finally {
    hideLoading();
    isFetching = false; // ✅ 플래그 해제
  }
}

/* ============================================================
   ✅ 테이블 렌더링 (최종 안정화 버전)
   ============================================================ */
export async function renderMainTable(rows = []) {
  const tbody = els.mainTable.querySelector("tbody");
  if (!tbody) return;

  // ✅ 기존 DataTable 완전 제거 (지연 포함)
  if (window.jQuery && $.fn.DataTable && $.fn.DataTable.isDataTable("#mainTable")) {
    $("#mainTable").DataTable().clear().destroy();
    await new Promise(r => setTimeout(r, 20)); // ⚠️ DOM 정리 시간 확보
  }

  // ✅ 테이블 내용 초기화
  tbody.innerHTML = "";

  // ✅ 데이터 없는 경우 (DataTable 미초기화)
  if (!rows.length) {
    console.log("ℹ️ 조회 결과 없음 — DataTable 미초기화, 메시지만 표시");
    tbody.innerHTML = `<tr><td colspan="14" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
    return;
  }

  // ✅ 데이터 있는 경우 행 렌더링
  const html = rows
    .map(
      (r) => `
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
        <td>${r.process_date || ""}</td>
        <td>
          ${
            ["superuser", "main_admin"].includes(window.currentUser.grade)
              ? `<button class="btn btn-sm btn-outline-danger btnDeleteRow" data-id="${r.id}">삭제</button>`
              : ""
          }
        </td>
      </tr>`
    )
    .join("");

  tbody.insertAdjacentHTML("beforeend", html);

  // ✅ 데이터 있을 때만 DataTable 활성화
  initDataTable();
  attachDeleteHandlers();
  console.log("✅ 메인시트 렌더링 및 DataTable 재초기화 완료");
}

/* ============================================================
   ✅ DataTables 초기화
   ============================================================ */
function initDataTable() {
  if (!window.jQuery || !window.jQuery.fn.DataTable) return;

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
    console.warn("⚠️ DataTable 초기화 중 오류 발생:", e);
  }
}
