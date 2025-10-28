/**
 * django_ma/static/js/common/search_user_modal.js
 * -----------------------------------------------------
 * 모든 앱에서 공통으로 사용하는 '대상자 검색 모달' 로직
 * - /api/accounts/search-user/ 엔드포인트 기반
 * - 검색 후 결과 표시 및 userSelected 이벤트 발행
 * -----------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("searchUserModal");
  if (!modalEl) return; // 모달이 없는 페이지에서는 무시

  const form = modalEl.querySelector("#searchUserForm");
  const input = modalEl.querySelector("#searchKeyword");
  const resultsBox = modalEl.querySelector("#searchResults");

  // ✅ 공통 API URL (accounts/api_views.py)
  const searchUrl = modalEl.dataset.searchUrl || "/api/accounts/search-user/";

  /** 🔍 검색 실행 */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyword = input.value.trim();
    if (!keyword) return alert("검색어를 입력하세요.");

    resultsBox.innerHTML = `<div class='text-center py-3 text-muted'>검색 중...</div>`;

    try {
      const response = await fetch(`${searchUrl}?q=${encodeURIComponent(keyword)}`);
      if (!response.ok) throw new Error("검색 실패");
      const data = await response.json();

      if (!data.results?.length) {
        resultsBox.innerHTML = `<div class='text-center py-3 text-danger'>검색 결과가 없습니다.</div>`;
        return;
      }

      // ✅ 결과 렌더링
      resultsBox.innerHTML = data.results
        .map(
          (u) => `
            <div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center selectable-user"
                 data-id="${u.id}"
                 data-name="${u.name}"
                 data-branch="${u.branch || ""}"
                 data-part="${u.part || ""}"
                 data-rank="${u.rank || ""}"
                 data-regist="${u.regist || ""}">
              <div>
                <strong>${u.name}</strong> (${u.id})
                ${u.regist ? ` <span class="text-muted">(${u.regist})</span>` : ""}<br>
                <small class="text-muted">${u.part || ""}${u.branch ? " " + u.branch : ""}</small>
              </div>
              <button class="btn btn-sm btn-outline-primary selectUserBtn">선택</button>
            </div>`
        )
        .join("");

      // ✅ 선택 이벤트 연결
      resultsBox.querySelectorAll(".selectUserBtn").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          const parent = ev.target.closest(".selectable-user");
          const selected = {
            id: parent.dataset.id,
            name: parent.dataset.name,
            branch: parent.dataset.branch,
            part: parent.dataset.part,
            rank: parent.dataset.rank,
            regist: parent.dataset.regist,
          };

          // 🔸 이벤트 발행 — 각 페이지에서 userSelected 이벤트 수신
          document.dispatchEvent(new CustomEvent("userSelected", { detail: selected }));

          // 모달 닫기
          const bsModal = bootstrap.Modal.getInstance(modalEl);
          if (bsModal) bsModal.hide();

          // 입력 초기화
          input.value = "";
          resultsBox.innerHTML = "";
        });
      });
    } catch (err) {
      console.error("❌ 검색 오류:", err);
      resultsBox.innerHTML = `<div class='text-center text-danger py-3'>검색 실패</div>`;
    }
  });
});
