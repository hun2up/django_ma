// static/js/partner/manage_structure/modal_search.js
import { els } from "./dom_refs.js";

export function setupModalSearch() {
  if (!els.searchForm) return;

  els.searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyword = els.searchKeyword?.value.trim();
    if (!keyword) return alert("검색어를 입력하세요.");

    const url = els.root.dataset.searchUserUrl || "/board/search-user/";
    try {
      const res = await fetch(`${url}?q=${encodeURIComponent(keyword)}`);
      if (!res.ok) throw new Error("검색 실패");
      const data = await res.json();

      if (!els.searchResults) return;
      if (!data.results?.length) {
        els.searchResults.innerHTML = `<div class="text-muted small mt-2">검색 결과가 없습니다.</div>`;
      } else {
        els.searchResults.innerHTML = data.results
          .map(
            (u) => `
            <div class="border rounded p-2 mb-1 d-flex justify-content-between align-items-center">
              <div>
                <strong>${u.name}</strong> (${u.id})
                ${u.regist ? ` <span class="text-muted">(${u.regist})</span>` : ""}<br>
                <small class="text-muted">${u.part || ""}${u.branch ? " " + u.branch : ""}</small>
              </div>
              <button type="button" class="btn btn-sm btn-outline-primary selectUserBtn"
                data-id="${u.id}" data-name="${u.name}" data-branch="${u.branch || ""}"
                data-part="${u.part || ""}" data-rank="${u.rank || ""}" data-regist="${u.regist || ""}">
                선택
              </button>
            </div>`
          )
          .join("");
      }
    } catch (err) {
      console.error(err);
      alert("검색 중 오류가 발생했습니다.");
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("selectUserBtn")) return;

    const btn = e.target;
    const userId = btn.dataset.id;
    const userName = btn.dataset.name;
    const userBranch = btn.dataset.branch || "";
    const userPart = btn.dataset.part || "";
    const userRank = btn.dataset.rank || "";
    const userRegist = btn.dataset.regist || "";

    const targetRow = els.inputTable.querySelector("tbody tr:last-child");
    if (!targetRow) return alert("입력 행이 존재하지 않습니다.");

    targetRow.querySelector("input[name='tg_id']").value = userId;
    targetRow.querySelector("input[name='tg_name']").value = userName;
    targetRow.querySelector("input[name='tg_branch']").value = `${userPart} ${userBranch}`;
    targetRow.querySelector("input[name='tg_rank']").value = userRank;
    const regEl = targetRow.querySelector("input[name='tg_regist']");
    if (regEl) regEl.value = userRegist;

    // 요청자 자동 입력
    targetRow.querySelector("input[name='rq_name']").value = window.currentUser?.name || "";
    targetRow.querySelector("input[name='rq_id']").value = window.currentUser?.id || "";
    targetRow.querySelector("input[name='rq_branch']").value = window.currentUser?.branch || "";

    // 모달 닫기 & 폼 초기화
    const modal = bootstrap.Modal.getInstance(document.getElementById("searchUserModal"));
    if (modal) modal.hide();
    if (els.searchResults) els.searchResults.innerHTML = "";
    if (els.searchKeyword) els.searchKeyword.value = "";
  });
}
