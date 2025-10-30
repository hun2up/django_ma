import { els } from "./dom_refs.js";
import {
  alertBox,
  showLoading,
  hideLoading,
  getCSRFToken,
  pad2,
} from "./utils.js";
import { attachDeleteHandlers } from "./delete.js";

export async function fetchData(ym = null, branchValue = null) {
  const y = ym ? ym.split("-")[0] : els.year.value;
  const m = ym ? ym.split("-")[1] : els.month.value;
  const b = branchValue ?? els.branch?.value ?? "";
  const ymValue = `${y}-${pad2(m)}`;

  showLoading("데이터 불러오는 중...");

  const grade = window.currentUser?.grade;
  if (grade === "superuser" && !b) {
    alertBox("지점을 선택해주세요.");
    hideLoading();
    return;
  }

  try {
    const url = `${els.root.dataset.dataFetchUrl}?month=${ymValue}&branch=${encodeURIComponent(b)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("조회 실패");
    const data = await res.json();
    renderMainTable(data.rows || []);
  } catch (err) {
    console.error("fetchData error:", err);
    alertBox("데이터를 불러오지 못했습니다.");
  } finally {
    hideLoading();
  }
}

export function renderMainTable(rows) {
  const tbody = els.mainTable.querySelector("tbody");
  tbody.innerHTML = "";

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="17" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
    return;
  }

  const canEditProcessDate = ["superuser", "main_admin"].includes(
    window.currentUser?.grade
  );
  const canDelete = ["superuser", "main_admin"].includes(
    window.currentUser?.grade
  );
  const updateUrl = els.root.dataset.updateProcessDateUrl;

  rows.forEach((r) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>${r.requester_name || "-"}</td>
        <td>${r.requester_id || "-"}</td>
        <td>${r.branch || "-"}</td>
        <td class="text-blue">${r.target_name || "-"}</td>
        <td>${r.target_id || "-"}</td>
        <td>${r.target_branch || "-"}</td>
        <td class="text-blue">${r.chg_branch || "-"}</td>
        <td>${r.rank || "-"}</td>
        <td class="text-blue">${r.chg_rank || "-"}</td>
        <td class="text-center">${r.or_flag ? "✅" : "❌"}</td>
        <td>${r.memo || "-"}</td>
        <td>${r.request_date || "-"}</td>
        <td class="text-blue">
          ${
            canEditProcessDate
              ? `<input type="date" class="form-control form-control-sm process-date-input"
                        value="${r.process_date || ""}" data-id="${r.id}">`
              : `${r.process_date || "-"}`
          }
        </td>
        <td>
          ${
            canDelete
              ? `<button class="btn btn-outline-danger btn-sm btnDeleteRow" data-id="${r.id}">삭제</button>`
              : `<button class="btn btn-outline-secondary btn-sm" disabled>삭제</button>`
          }
        </td>
      </tr>
      `
    );
  });

  // 삭제 버튼 다시 바인딩
  attachDeleteHandlers();
}
