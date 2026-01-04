// django_ma/static/js/partner/manage_efficiency/delete.js
//
// ✅ Delete handlers (event delegation, single bind)
// - data-action="delete-row"   + data-row-id="..."
// - data-action="delete-group" + data-group-id="confirm_group_id"
// - dataset URL 키 혼재 대비: dataDeleteRowUrl / dataDataDeleteRowUrl 둘 다 읽기
// - 삭제 후 fetchData 재조회

import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";
import { fetchData } from "./fetch.js";
import { els } from "./dom_refs.js";

function str(v) {
  return String(v ?? "").trim();
}

function getRoot() {
  return (
    els.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-calculate") ||
    document.getElementById("manage-structure")
  );
}

function getDataset(root) {
  return root?.dataset || {};
}

// ✅ dataset 키가 헷갈리는 경우가 많아서 모두 허용
function getDeleteRowUrl() {
  const ds = getDataset(getRoot());
  return str(ds.dataDeleteRowUrl || ds.deleteRowUrl || ds.dataDataDeleteRowUrl || "");
}

function getDeleteGroupUrl() {
  const ds = getDataset(getRoot());
  return str(ds.dataDeleteGroupUrl || ds.deleteGroupUrl || ds.dataDataDeleteGroupUrl || "");
}

function currentYM() {
  const y = str(els.year?.value);
  const m = str(els.month?.value);
  if (!y || !m) return "";
  return `${y}-${m}`;
}

function currentBranch() {
  return str(els.branch?.value);
}

async function refreshAfterDelete() {
  const ym = currentYM();
  const branch = currentBranch();
  if (ym && branch) {
    await fetchData(ym, branch);
  }
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify(body || {}),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.status !== "success") {
    throw new Error(data.message || `요청 실패 (${res.status})`);
  }
  return data;
}

export function attachEfficiencyDeleteHandlers() {
  const root = getRoot();
  if (!root) return;

  // ✅ 중복 바인딩 방지
  if (root.dataset.deleteInited === "1") return;
  root.dataset.deleteInited = "1";

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = str(btn.dataset.action);

    // -------------------------------------------------
    // ✅ Row delete
    // -------------------------------------------------
    if (action === "delete-row") {
      const rowId = str(btn.dataset.rowId);
      if (!rowId) return;

      if (!confirm("해당 행을 삭제할까요?")) return;

      const url = getDeleteRowUrl();
      if (!url) {
        return alertBox("행 삭제 URL이 없습니다. (data-data-delete-row-url 확인)");
      }

      try {
        showLoading("삭제 중...");
        btn.disabled = true;

        await postJson(url, { id: rowId });
        await refreshAfterDelete();
      } catch (err) {
        console.error(err);
        alertBox(err.message || "삭제 중 오류");
      } finally {
        btn.disabled = false;
        hideLoading();
      }
      return;
    }

    // -------------------------------------------------
    // ✅ Group delete
    // -------------------------------------------------
    if (action === "delete-group") {
      const gid = str(btn.dataset.groupId);
      if (!gid) return;

      if (!confirm("이 그룹 전체를 삭제할까요?\n(그룹 내 저장된 행/첨부도 함께 삭제됩니다)")) return;

      const url = getDeleteGroupUrl();
      if (!url) {
        return alertBox("그룹 삭제 URL이 없습니다. (data-data-delete-group-url 확인)");
      }

      try {
        showLoading("그룹 삭제 중...");
        btn.disabled = true;

        await postJson(url, { confirm_group_id: gid });
        await refreshAfterDelete();
      } catch (err) {
        console.error(err);
        alertBox(err.message || "그룹 삭제 중 오류");
      } finally {
        btn.disabled = false;
        hideLoading();
      }
      return;
    }
  });
}
