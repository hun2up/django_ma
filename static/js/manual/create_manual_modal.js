// django_ma/static/js/manual/create_manual_modal.js
// -----------------------------------------------------------------------------
// Create Manual Modal (FINAL - Refactor)
// - 기존 기능 유지: 라디오 공개범위/CSRF/redirect_url 이동/HTML(403) 안전 처리
// - 공통 유틸은 ManualShared 사용
// -----------------------------------------------------------------------------

(() => {
  const S = window.ManualShared;
  if (!S) {
    console.error("[create_manual_modal] ManualShared not loaded. (_shared.js 포함 확인)");
    return;
  }

  const { ready, toStr, getCSRFTokenFromForm, setBtnLoading, showErrorBox, clearErrorBox, safeReadJson } = S;

  function getSelectedAccess(formEl) {
    const el = formEl?.querySelector?.('input[name="manualAccess"]:checked');
    return toStr(el?.value || "normal"); // 기본 normal
  }

  function setDefaultAccess(formEl) {
    const normal = formEl?.querySelector?.("#manualAccessNormal");
    if (normal) normal.checked = true;
  }

  function toFlags(access) {
    // 서버 payload는 admin_only/staff_only로도 보내지만(기존 유지),
    // 서버는 access 기준으로 처리하므로 이 값은 “호환 목적”으로만 유지
    return {
      admin_only: access === "admin",
      staff_only: access === "staff",
    };
  }

  ready(() => {
    const modalEl = document.getElementById("createManualModal");
    if (!modalEl) return;

    // 중복 바인딩 방지
    if (modalEl.dataset.bound === "true") return;
    modalEl.dataset.bound = "true";

    const form = modalEl.querySelector("#createManualForm");
    const input = modalEl.querySelector("#manualTitleInput");
    const errBox = modalEl.querySelector("#manualCreateError");
    const btn = modalEl.querySelector("#btnCreateManualConfirm");

    const createUrl = toStr(modalEl.dataset.createUrl || "");

    if (!form || !input || !btn) {
      console.error("[create_manual_modal] form/input/btn not found", { form, input, btn });
      return;
    }
    if (!createUrl) {
      console.error("[create_manual_modal] createUrl is empty (data-create-url 확인 필요)");
      return;
    }

    function resetUI() {
      clearErrorBox(errBox);
      input.value = "";
      setDefaultAccess(form);
      setBtnLoading(btn, false, null, "만들기");
    }

    modalEl.addEventListener("shown.bs.modal", () => {
      resetUI();
      setTimeout(() => input.focus(), 0);
    });

    modalEl.addEventListener("hidden.bs.modal", resetUI);

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearErrorBox(errBox);

      const title = toStr(input.value);
      if (!title) return showErrorBox(errBox, "매뉴얼 이름을 입력해주세요.");
      if (title.length > 80) return showErrorBox(errBox, "매뉴얼 이름은 80자 이하여야 합니다.");

      const csrf = getCSRFTokenFromForm(form);
      if (!csrf) {
        return showErrorBox(
          errBox,
          "CSRF 토큰을 찾을 수 없습니다. (form 안에 {% csrf_token %} 추가했는지 확인해주세요)"
        );
      }

      const access = getSelectedAccess(form); // normal/admin/staff
      const { admin_only, staff_only } = toFlags(access);

      // DOM 조작 대비 최종 방어(기존 로직 유지)
      if (admin_only && staff_only) {
        return showErrorBox(errBox, "공개 범위는 하나만 선택 가능합니다.");
      }

      setBtnLoading(btn, true, "생성중...", "만들기");

      try {
        const res = await fetch(createUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ title, access, admin_only, staff_only }),
        });

        const data = await safeReadJson(res);
        if (data?.__non_json__) throw new Error(`생성 실패 (HTTP ${res.status})`);
        if (!res.ok || !data?.ok) throw new Error(data?.message || `생성 실패 (HTTP ${res.status})`);

        const redirectUrl = toStr(data.redirect_url);
        if (!redirectUrl) throw new Error("redirect_url이 응답에 없습니다.");

        window.location.href = redirectUrl;
      } catch (err) {
        console.error("[create_manual_modal] error", err);
        showErrorBox(errBox, err?.message || "오류가 발생했습니다.");
        setBtnLoading(btn, false, null, "만들기");
      }
    });
  });
})();
