// django_ma/static/js/manual/create_manual_modal.js
// --------------------------------------------------
// ✅ Create Manual Modal (FINAL - Radio Options)
// - CSRF: form 내 {% csrf_token %} hidden input에서 읽음 (CSRF_COOKIE_HTTPONLY=True 대응)
// - 중복 바인딩 방지
// - 공개범위: 라디오 3개(일반/관리자전용/직원전용), 기본값=일반
// - 서버 전송: admin_only, staff_only (둘 다 true 불가)
// - 응답이 JSON이 아닐 때(예: CSRF 403 HTML)도 안전 처리
// - 성공 시 redirect_url로 이동
// --------------------------------------------------

(() => {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[create_manual_modal]", ...a);

  /* -----------------------------
   * helpers
   * ----------------------------- */
  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  }

  function toStr(v) {
    return String(v ?? "").trim();
  }

  function getCSRFTokenFromForm(formEl) {
    const el = formEl?.querySelector?.('input[name="csrfmiddlewaretoken"]');
    return toStr(el?.value || "");
  }

  function setBtnLoading(btn, isLoading) {
    if (!btn) return;
    if (isLoading) {
      btn.dataset.oldText = btn.textContent || "만들기";
      btn.disabled = true;
      btn.textContent = "생성중...";
    } else {
      btn.disabled = false;
      btn.textContent = btn.dataset.oldText || "만들기";
      delete btn.dataset.oldText;
    }
  }

  function showError(errBox, msg) {
    const m = toStr(msg) || "오류가 발생했습니다.";
    if (!errBox) return window.alert(m);
    errBox.textContent = m;
    errBox.classList.remove("d-none");
  }

  function clearError(errBox) {
    if (!errBox) return;
    errBox.textContent = "";
    errBox.classList.add("d-none");
  }

  async function safeReadJson(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      const text = await res.text().catch(() => "");
      return { __non_json__: true, __text__: text };
    }
    return await res.json().catch(() => ({}));
  }

  function getSelectedAccess(formEl) {
    // name="manualAccess" 라디오에서 선택값 읽음
    const el = formEl?.querySelector?.('input[name="manualAccess"]:checked');
    return toStr(el?.value || "normal"); // 기본 normal
  }

  function setDefaultAccess(formEl) {
    const normal = formEl?.querySelector?.("#manualAccessNormal");
    if (normal) normal.checked = true;
  }

  function toFlags(access) {
    // 서버 payload는 admin_only/staff_only로 통일
    const admin_only = access === "admin";
    const staff_only = access === "staff";
    return { admin_only, staff_only };
  }

  /* -----------------------------
   * init
   * ----------------------------- */
  ready(() => {
    const modalEl = document.getElementById("createManualModal");
    if (!modalEl) return;

    // ✅ 중복 바인딩 방지
    if (modalEl.dataset.bound === "true") return;
    modalEl.dataset.bound = "true";

    const form = modalEl.querySelector("#createManualForm");
    const input = modalEl.querySelector("#manualTitleInput");
    const errBox = modalEl.querySelector("#manualCreateError");
    const btn = modalEl.querySelector("#btnCreateManualConfirm");

    const createUrl = toStr(modalEl.dataset.createUrl || "");
    log("init", { createUrl });

    if (!form || !input || !btn) {
      console.error("[create_manual_modal] form/input/btn not found", { form, input, btn });
      return;
    }
    if (!createUrl) {
      console.error("[create_manual_modal] createUrl is empty (data-create-url 확인 필요)");
      return;
    }

    // 모달 열릴 때 초기화
    modalEl.addEventListener("shown.bs.modal", () => {
      clearError(errBox);
      input.value = "";
      setDefaultAccess(form);     // ✅ 기본값: 일반
      setBtnLoading(btn, false);
      setTimeout(() => input.focus(), 0);
    });

    // 모달 닫힐 때 초기화
    modalEl.addEventListener("hidden.bs.modal", () => {
      clearError(errBox);
      input.value = "";
      setBtnLoading(btn, false);
      setDefaultAccess(form);
    });

    // submit
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearError(errBox);

      const title = toStr(input.value);
      if (!title) return showError(errBox, "매뉴얼 이름을 입력해주세요.");
      if (title.length > 80) return showError(errBox, "매뉴얼 이름은 80자 이하여야 합니다.");

      const csrf = getCSRFTokenFromForm(form);
      if (!csrf) {
        return showError(
          errBox,
          "CSRF 토큰을 찾을 수 없습니다. (form 안에 {% csrf_token %} 추가했는지 확인해주세요)"
        );
      }

      const access = getSelectedAccess(form); // normal/admin/staff
      const { admin_only, staff_only } = toFlags(access);

      // ✅ 최종 방어 (DOM 조작 대비)
      if (admin_only && staff_only) {
        return showError(errBox, "공개 범위는 하나만 선택 가능합니다.");
      }

      setBtnLoading(btn, true);

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
        log("response", { status: res.status, data });

        if (data?.__non_json__) throw new Error(`생성 실패 (HTTP ${res.status})`);
        if (!res.ok || !data?.ok) throw new Error(data?.message || `생성 실패 (HTTP ${res.status})`);

        const redirectUrl = toStr(data.redirect_url);
        if (!redirectUrl) throw new Error("redirect_url이 응답에 없습니다.");

        window.location.href = redirectUrl;
      } catch (err) {
        console.error("[create_manual_modal] error", err);
        showError(errBox, err?.message || "오류가 발생했습니다.");
        setBtnLoading(btn, false);
      }
    });
  });
})();
