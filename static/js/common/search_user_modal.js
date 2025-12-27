/**
 * django_ma/static/js/common/search_user_modal.js
 * -----------------------------------------------------
 * 공통 대상자 검색 모달
 * - /api/accounts/search-user/ 기반
 * - 결과 클릭 시 userSelected 이벤트 발행
 * - 필드가 없으면 건너뛰도록 안전 처리
 * -----------------------------------------------------
 */
document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("searchUserModal");
  if (!modalEl || modalEl.dataset.bound) return;
  modalEl.dataset.bound = "true";

  const form = modalEl.querySelector("#searchUserForm");
  const input = modalEl.querySelector("#searchKeyword");
  const resultsBox = modalEl.querySelector("#searchResults");
  const searchUrl = modalEl.dataset.searchUrl || "/api/accounts/search-user/";

  /* ---------------------------
     🔍 검색
  --------------------------- */
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const keyword = input?.value?.trim() || "";
      if (!keyword) {
        window.alert("검색어를 입력하세요.");
        return;
      }

      resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

      try {
        const res = await fetch(`${searchUrl}?q=${encodeURIComponent(keyword)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!res.ok) throw new Error("검색 실패");
        const data = await res.json();

        if (!data.results?.length) {
          resultsBox.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
          return;
        }

        resultsBox.innerHTML = data.results
          .map(
            (user) => `
            <button type="button" class="list-group-item list-group-item-action search-result"
              data-id="${user.id}"
              data-name="${user.name}"
              data-branch="${user.branch || ""}"
              data-rank="${user.rank || ""}"
              data-part="${user.part || ""}"
              data-regist="${user.regist || ""}"
              data-enter="${user.enter || ""}"
              data-quit="${user.quit || "재직중"}">
              <div class="d-flex justify-content-between">
                <span><strong>${user.name}</strong> (${user.id}) (${user.regist || "-"})</span>
                <small class="text-muted">${user.branch || ""}</small>
              </div>
              <small class="text-muted">
                입사일: ${user.enter || "-"} / 퇴사일: ${user.quit || "-"}
              </small>
            </button>
          `
          )
          .join("");
      } catch (err) {
        console.error("❌ 검색 오류:", err);
        resultsBox.innerHTML = `<div class="text-center text-danger py-3">검색 실패</div>`;
      }
    });
  }

  /* ---------------------------
     ✅ 결과 클릭 → userSelected
  --------------------------- */
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

    const bsModal = bootstrap.Modal.getInstance(modalEl);
    if (bsModal) bsModal.hide();

    if (input) input.value = "";
    if (resultsBox) resultsBox.innerHTML = "";
  });

  /* ---------------------------
     모달 닫힐 때 초기화
  --------------------------- */
  modalEl.addEventListener("hidden.bs.modal", () => {
    if (input) input.value = "";
    if (resultsBox) resultsBox.innerHTML = "";
  });
});

/* -----------------------------------------------------
 * 검색 버튼 누른 행을 active 로 표시
 * ----------------------------------------------------- */
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("btnOpenSearch")) {
    document.querySelectorAll(".input-row").forEach((r) => r.classList.remove("active"));
    const row = e.target.closest(".input-row");
    if (row) row.classList.add("active");
  }
});

/* -----------------------------------------------------
 * userSelected → 있는 필드만 채우기 (공통 최소치)
 * ----------------------------------------------------- */
document.addEventListener("userSelected", (e) => {
  const activeRow = document.querySelector(".input-row.active");
  if (!activeRow) return;

  const user = e.detail || {};

  const tgName = activeRow.querySelector('input[name="tg_name"]');
  if (tgName) tgName.value = user.name || "";

  const tgId = activeRow.querySelector('input[name="tg_id"]');
  if (tgId) tgId.value = user.id || "";

  const tgBranch = activeRow.querySelector('input[name="tg_branch"]');
  if (tgBranch) tgBranch.value = user.branch || "";

  const tgRank = activeRow.querySelector('input[name="tg_rank"]');
  if (tgRank) tgRank.value = user.rank || "";
});
