/**
 * django_ma/static/js/common/search_user_modal.js  (PATCHED)
 * -----------------------------------------------------
 * 공통 대상자 검색 모달
 * - /api/accounts/search-user/ 기반
 * - ✅ manage-structure / manage-rate 에서만 scope=branch 전송
 * - ✅ deposit-home도 root로 인식 (채권관리 페이지 포함)
 * - ✅ 결과 클릭 시 userSelected 이벤트 document + window 모두 발행
 * - ✅ 클릭 위임을 resultsBox에만 걸어 충돌/미발행 방지
 * -----------------------------------------------------
 */

function getActiveRoot() {
  return (
    document.getElementById("manage-structure") ||
    document.getElementById("manage-rate") ||
    document.getElementById("manage-table") ||
    document.getElementById("deposit-home") || // ✅ 채권관리 페이지 추가
    null
  );
}

function getPageScope(root) {
  const id = root?.id || "";
  if (id === "manage-structure" || id === "manage-rate") return "branch";
  return "default";
}

function getEffectiveBranchForSearch(root) {
  const grade = (
    root?.dataset?.userGrade ||
    window.currentUser?.grade ||
    ""
  ).toString().trim();

  const sel = document.getElementById("branchSelect");
  const selectedBranch = (sel?.value || "").toString().trim();

  const uBranch = (window.currentUser?.branch || "").toString().trim();
  const dsBranch = (root?.dataset?.defaultBranch || "").toString().trim();

  if (grade === "superuser") return selectedBranch || uBranch || dsBranch;
  return uBranch || dsBranch || selectedBranch;
}

document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("searchUserModal");
  if (!modalEl || modalEl.dataset.bound) return;
  modalEl.dataset.bound = "true";

  const root = getActiveRoot();
  const scope = getPageScope(root);

  const form = modalEl.querySelector("#searchUserForm");
  const input = modalEl.querySelector("#searchKeyword");
  const resultsBox = modalEl.querySelector("#searchResults");
  const searchUrl = modalEl.dataset.searchUrl || "/api/accounts/search-user/";

  if (!form || !resultsBox) {
    console.warn("[search_user_modal] form/resultsBox not found");
    return;
  }

  // 🔍 검색
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const keyword = input?.value?.trim() || "";
    if (!keyword) {
      window.alert("검색어를 입력하세요.");
      return;
    }

    // ✅ default scope 페이지(deposit 등)에서는 root 없어도 검색 허용
    // ✅ branch scope(편제/요율)만 root/branch 필수
    let branch = "";
    if (scope === "branch") {
      if (!root) {
        window.alert("페이지 루트를 찾을 수 없습니다.");
        return;
      }
      branch = getEffectiveBranchForSearch(root);
      if (!branch) {
        window.alert("지점 정보가 없습니다. (부서/지점을 먼저 선택하거나 로그인 사용자 지점 확인)");
        return;
      }
    }

    resultsBox.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

    try {
      const url = new URL(searchUrl, window.location.origin);
      url.searchParams.set("q", keyword);

      if (scope === "branch") {
        url.searchParams.set("scope", "branch");
        url.searchParams.set("branch", branch);
      }

      const res = await fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();

      if (!data.results?.length) {
        resultsBox.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
        return;
      }

      resultsBox.innerHTML = data.results
        .map(
          (user) => `
          <button type="button"
            class="list-group-item list-group-item-action search-result"
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

  // ✅ 결과 클릭 → userSelected (resultsBox에만 위임)
  resultsBox.addEventListener("click", (e) => {
    const item = e.target.closest?.(".search-result");
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

    // ✅ document + window 둘 다 발행 (수신 안정화)
    const ev = new CustomEvent("userSelected", { detail: selected });
    document.dispatchEvent(ev);
    window.dispatchEvent(ev);

    // 모달 닫기 (bootstrap 없으면 무시)
    try {
      const bsModal = window.bootstrap?.Modal?.getInstance?.(modalEl);
      if (bsModal) bsModal.hide();
    } catch (_) {}

    if (input) input.value = "";
    resultsBox.innerHTML = "";
  });

  // 모달 닫힐 때 초기화
  modalEl.addEventListener("hidden.bs.modal", () => {
    if (input) input.value = "";
    resultsBox.innerHTML = "";
  });
});
