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
  if (!modalEl || modalEl.dataset.bound) return; // 모달 없는 페이지는 무시

  const form = modalEl.querySelector("#searchUserForm");
  const input = modalEl.querySelector("#searchKeyword");
  const resultsBox = modalEl.querySelector("#searchResults");

  const searchUrl = modalEl.dataset.searchUrl || "/api/accounts/search-user/";

  /** 🔍 검색 실행 */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyword = input.value.trim();
    if (!keyword) return alert("검색어를 입력하세요.");

    resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

    try {
      const res = await fetch(`${searchUrl}?q=${encodeURIComponent(keyword)}`);
      if (!res.ok) throw new Error("검색 실패");
      const data = await res.json();

      if (!data.results?.length) {
        resultsBox.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
        return;
      }

      // ✅ 기존 support_form 스타일로 렌더링
      resultsBox.innerHTML = data.results
        .map(
          (user) => `
        <button type="button" class="list-group-item list-group-item-action search-result"
          data-id="${user.id}"
          data-name="${user.name}"
          data-branch="${user.branch}"
          data-part="${user.part || ''}"
          data-regist="${user.regist || ''}"
          data-enter="${user.enter || ''}"
          data-quit="${user.quit || '재직중'}">
          <div class="d-flex justify-content-between">
            <span><strong>${user.name}</strong> (${user.id}) (${user.regist || '-'})</span>
            <small class="text-muted">${user.branch || ''}</small>
          </div>
          <small class="text-muted">
            입사일: ${user.enter || '-'} / 퇴사일: ${user.quit || '-'}
          </small>
        </button>`
        )
        .join("");
    } catch (err) {
      console.error("❌ 검색 오류:", err);
      resultsBox.innerHTML = `<div class="text-center text-danger py-3">검색 실패</div>`;
    }
  });

  /** ✅ 결과 클릭 시 전역 이벤트(userSelected) 발행 */
  document.addEventListener("click", (e) => {
    const item = e.target.closest(".search-result");
    if (!item) return;

    const selected = {
      id: item.dataset.id,
      name: item.dataset.name,
      branch: item.dataset.branch,
      part: item.dataset.part,
      regist: item.dataset.regist,
      enter: item.dataset.enter,
      quit: item.dataset.quit,
    };

    document.dispatchEvent(new CustomEvent("userSelected", { detail: selected }));

    // 모달 닫기
    const bsModal = bootstrap.Modal.getInstance(modalEl);
    if (bsModal) bsModal.hide();

    // 초기화
    input.value = "";
    resultsBox.innerHTML = "";
  });

  /** 🔁 모달 닫힐 때 자동 초기화 */
  modalEl.addEventListener("hidden.bs.modal", () => {
    input.value = "";
    resultsBox.innerHTML = "";
  });
});
