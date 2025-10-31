import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, pad2 } from "./utils.js";
import { attachDeleteHandlers } from "./delete.js";

/**
 * ✅ 데이터 조회 및 렌더링
 */
export async function fetchData(ym = null, branchValue = null, meta = {}) {
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
    const text = await res.text();
    console.log("📦 Raw Response:", text);

    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const data = JSON.parse(text);
    if (data.status !== "success") throw new Error(data.message || "조회 실패");

    renderMainTable(data.rows || []);
    console.log(`✅ 데이터 로드 완료: ${data.rows?.length || 0}건`);
  } catch (err) {
    console.error("❌ fetchData 에러:", err);
    alertBox("데이터를 불러오지 못했습니다.");
  } finally {
    hideLoading();
  }
}

/* ============================================================
   ✅ 테이블 렌더링
   ============================================================ */
export function renderMainTable(rows) {
  const tbody = els.mainTable.querySelector("tbody");
  if (!tbody) return;

  // 기존 DataTable 완전 제거
  if (window.jQuery && $.fn.DataTable && $.fn.DataTable.isDataTable("#mainTable")) {
    $("#mainTable").DataTable().clear().destroy();
  }

  // 내용 렌더링
  tbody.innerHTML = "";
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="14" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
  } else {
    for (const r of rows) {
      tbody.insertAdjacentHTML(
        "beforeend",
        `
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
        </tr>
        `
      );
    }
  }

  // DataTables 재초기화
  initDataTable();
  attachDeleteHandlers();
  console.log("✅ 메인시트 렌더링 및 DataTable 재초기화 완료");
}

/* ============================================================
   ✅ DataTables 초기화
   ============================================================ */
function initDataTable() {
  if (!window.jQuery || !window.jQuery.fn.DataTable) return;

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
  });
}
