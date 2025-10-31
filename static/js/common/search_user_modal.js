/**
 * django_ma/static/js/common/search_user_modal.js
 * -----------------------------------------------------
 * 모든 앱에서 공통으로 사용하는 '대상자 검색 모달' 로직
 * - /api/accounts/search-user/ 엔드포인트 기반
 * - 검색 후 결과 표시 및 선택 시 'userSelected' 이벤트 발행
 * - 선택된 사용자 정보를 활성 행(input-row.active)에 자동 반영
 * -----------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("searchUserModal");
  if (!modalEl || modalEl.dataset.bound) return; // 모달 없는 페이지는 무시
  modalEl.dataset.bound = "true";

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

      // ✅ 검색 결과 목록 렌더링
      resultsBox.innerHTML = data.results
        .map(
          (user) => `
        <button type="button" class="list-group-item list-group-item-action search-result"
          data-id="${user.id}"
          data-name="${user.name}"
          data-branch="${user.branch || ''}"
          data-rank="${user.rank || ''}"
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
      rank: item.dataset.rank,
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

/* -----------------------------------------------------
 * 📌 추가: userSelected 이벤트 핸들러
 * ----------------------------------------------------- */
document.addEventListener("userSelected", (e) => {
  const user = e.detail;
  const activeRow = document.querySelector(".input-row.active");
  if (!activeRow) {
    console.warn("⚠️ 활성화된 입력 행이 없습니다.");
    return;
  }

  // ✅ 선택된 행의 대상자 필드 채우기
  activeRow.querySelector('input[name="tg_name"]').value = user.name || "";
  activeRow.querySelector('input[name="tg_id"]').value = user.id || "";
  activeRow.querySelector('input[name="tg_branch"]').value = user.branch || "";
  activeRow.querySelector('input[name="tg_rank"]').value = user.rank || "";

  // ✅ 선택 후 active 클래스 제거 (다음 선택 시 초기화)
  activeRow.classList.remove("active");
});

/* -----------------------------------------------------
 * 📌 검색 버튼 클릭 시 행 활성화 처리
 * ----------------------------------------------------- */
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("btnOpenSearch")) {
    document.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    const row = e.target.closest(".input-row");
    if (row) row.classList.add("active");
  }
});
