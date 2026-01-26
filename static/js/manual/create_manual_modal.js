// django_ma/static/js/manual/create_manual_modal.js
// ============================================================================
// Create Manual Modal
// - 매뉴얼 생성 전용
// - CSRF / access radio / redirect 처리
// ============================================================================

(() => {
  const S = window.ManualShared;
  if (!S) {
    console.error("[create_manual_modal] ManualShared not loaded.");
    return;
  }

  const {
    ready,
    toStr,
    getCSRFTokenFromForm,
    setBtnLoading,
    showErrorBox,
    clearErrorBox,
    safeReadJson,
  } = S;

  ready(() => {
    const modal = document.getElementById("createManualModal");
    if (!modal || modal.dataset.bound) return;
    modal.dataset.bound = "true";

    const form = modal.querySelector("#createManualForm");
    const input = modal.querySelector("#manualTitleInput");
    const errBox = modal.querySelector("#manualCreateError");
    const btn = modal.querySelector("#btnCreateManualConfirm");

    const createUrl = toStr(modal.dataset.createUrl);
    if (!form || !input || !btn || !createUrl) return;

    function reset() {
      clearErrorBox(errBox);
      input.value = "";
      setBtnLoading(btn, false, null, "만들기");
      form.querySelector("#manualAccessNormal").checked = true;
    }

    modal.addEventListener("shown.bs.modal", () => {
      reset();
      input.focus();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearErrorBox(errBox);

      const title = toStr(input.value);
      if (!title) return showErrorBox(errBox, "매뉴얼 이름을 입력해주세요.");
      if (title.length > 80) return showErrorBox(errBox, "80자 이하여야 합니다.");

      const csrf = getCSRFTokenFromForm(form);
      const access = toStr(form.querySelector('input[name="manualAccess"]:checked')?.value);

      setBtnLoading(btn, true, "생성중...");

      try {
        const res = await fetch(createUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ title, access }),
        });

        const data = await safeReadJson(res);
        if (!res.ok || !data?.ok) throw new Error(data?.message);

        window.location.href = toStr(data.redirect_url);
      } catch (err) {
        showErrorBox(errBox, err.message);
        setBtnLoading(btn, false, null, "만들기");
      }
    });
  });
})();
