import { els } from "./dom_refs.js";
import { alertBox, showLoading, hideLoading, pad2 } from "./utils.js";
import { attachDeleteHandlers } from "./delete.js";

export async function fetchData(ym = null, branchValue = null) {
  const y = ym ? ym.split("-")[0] : els.year?.value;
  const m = ym ? ym.split("-")[1] : els.month?.value;
  const b = branchValue ?? els.branch?.value ?? "";
  const ymValue = `${y}-${pad2(m)}`;

  console.log("🚀 fetchData() 실행:", { ymValue, branch: b });

  showLoading("데이터 불러오는 중...");

  const grade = window.currentUser?.grade;
  if (grade === "superuser" && !b) {
    alertBox("지점을 선택해주세요.");
    hideLoading();
    return;
  }

  try {
    const url = `${els.root.dataset.dataFetchUrl}?month=${ymValue}&branch=${encodeURIComponent(b)}`;
    console.log("📡 서버 요청 URL:", url);
    const res = await fetch(url);
    console.log("📨 서버 응답 상태:", res.status);
    if (!res.ok) throw new Error("조회 실패");

    const data = await res.json();
    console.log("📦 응답 데이터:", data);

    if (!data || !data.rows) {
      console.warn("⚠️ rows 데이터 없음:", data);
    }
    renderMainTable(data.rows || []);
  } catch (err) {
    console.error("❌ fetchData 에러:", err);
    alertBox("데이터를 불러오지 못했습니다.");
  } finally {
    hideLoading();
  }
}

export function renderMainTable(rows) {
  console.log("📊 renderMainTable 실행:", rows?.length);
  const tbody = els.mainTable.querySelector("tbody");
  tbody.innerHTML = "";

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="17" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
    return;
  }

  rows.forEach((r) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
        <tr>
          <td>${r.requester_name || "-"}</td>
          <td>${r.requester_id || "-"}</td>
          <td>${r.branch || "-"}</td>
          <td>${r.target_name || "-"}</td>
          <td>${r.target_id || "-"}</td>
          <td>${r.target_branch || "-"}</td>
          <td>${r.chg_branch || "-"}</td>
          <td>${r.rank || "-"}</td>
          <td>${r.chg_rank || "-"}</td>
          <td>${r.or_flag ? "✅" : "❌"}</td>
          <td>${r.memo || "-"}</td>
          <td>${r.request_date || "-"}</td>
          <td>${r.process_date || "-"}</td>
          <td>-</td>
        </tr>
      `
    );
  });

  attachDeleteHandlers();
}
