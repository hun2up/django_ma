// django_ma/static/js/board/common/detail_inline_update.js
// =========================================================
// Board Common Inline Update (DETAIL) (FINAL)
// - post_detail / task_detail 공용
// - superuser 담당자/상태 select 변경 AJAX
// - detail 화면의 #statusUpdatedAtText 갱신
// - onSuccess 공식 지원 (예: status_ui 재적용)
//
// ✅ CSS 모듈화 대응
// - 인라인 style(pointerEvents/opacity) 주입 제거
// - disabled + aria-busy + classList('is-busy') 토글 방식
// =========================================================

(function () {
  "use strict";

  const Board = (window.Board = window.Board || {});
  Board.Common = Board.Common || {};

  const INIT_FLAG = "__boardDetailInlineUpdateBound";

  /* =========================================================
   * 1) Utilities
   * ========================================================= */
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function safeJson(res) {
    return res.json().catch(() => null);
  }

  function getCsrfFromForm(form) {
    return form?.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";
  }

  function setBusy(selectEl, busy) {
    if (!selectEl) return;

    // ✅ 인라인 style 대신: disabled + class
    if (busy) selectEl.setAttribute("disabled", "disabled");
    else selectEl.removeAttribute("disabled");

    selectEl.setAttribute("aria-busy", busy ? "true" : "false");
    selectEl.classList.toggle("is-busy", !!busy);
  }

  function showAlert(alertHost, message, type = "success") {
    if (!alertHost) return window.alert(message || "");
    alertHost.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show text-center" role="alert">
        ${escapeHtml(message || "")}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;

    window.setTimeout(() => {
      const el = qs(".alert", alertHost);
      if (!el) return;
      try {
        bootstrap.Alert.getOrCreateInstance(el).close();
      } catch {
        el.remove();
      }
    }, 2500);
  }

  async function sendUpdate({ updateUrl, form, actionType, value }) {
    const csrf = getCsrfFromForm(form);
    if (!csrf) throw new Error("CSRF 토큰을 찾을 수 없습니다.");

    const body = new URLSearchParams();
    body.set("action_type", actionType);
    body.set("value", value);

    const res = await fetch(updateUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: body.toString(),
      credentials: "same-origin",
    });

    const data = await safeJson(res);
    if (!res.ok || !data?.ok) {
      throw new Error(data?.message || `변경 실패 (HTTP ${res.status})`);
    }
    return data;
  }

  /* =========================================================
   * 2) Public init
   * ========================================================= */
  /**
   * initDetailInlineUpdate
   * @param {Object} opts
   * @param {string} opts.bootId - "postDetailBoot" | "taskDetailBoot"
   * @param {Function} [opts.onSuccess] - (data, ctx) => void
   */
  Board.Common.initDetailInlineUpdate = function initDetailInlineUpdate(opts) {
    const bootId = opts?.bootId;
    const onSuccess = typeof opts?.onSuccess === "function" ? opts.onSuccess : null;
    if (!bootId) return;

    const bind = () => {
      // 중복 바인딩 방지(DETAIL 페이지는 1회만)
      if (document.body.dataset[INIT_FLAG] === "1") return;
      document.body.dataset[INIT_FLAG] = "1";

      const boot = document.getElementById(bootId);
      const updateUrl = boot?.dataset?.updateUrl || "";
      if (!updateUrl) return; // 비-superuser 화면 등

      const alertHost = document.getElementById("inlineUpdateAlertHost");
      const statusUpdatedAtText = document.getElementById("statusUpdatedAtText");

      // 초기 prevValue
      document
        .querySelectorAll(
          "form.inline-update-form select[name='handler'], form.inline-update-form select[name='status']"
        )
        .forEach((s) => (s.dataset.prevValue = s.value));

      document.addEventListener("change", async (e) => {
        const sel = e.target;
        if (!(sel instanceof HTMLSelectElement)) return;

        const form = sel.closest("form.inline-update-form");
        if (!form) return;

        const name = sel.getAttribute("name");
        if (name !== "handler" && name !== "status") return;

        const actionType = qs('input[name="action_type"]', form)?.value || "";
        if (!actionType) {
          showAlert(alertHost, "action_type이 없습니다.", "danger");
          return;
        }

        if (form.dataset.submitting === "1") return;
        form.dataset.submitting = "1";

        const prev = sel.dataset.prevValue ?? sel.value;
        sel.dataset.prevValue = sel.value;

        setBusy(sel, true);

        try {
          const data = await sendUpdate({ updateUrl, form, actionType, value: sel.value });

          // 서버가 status를 돌려주면 확정 반영
          if (actionType === "status" && data.status) {
            sel.value = data.status;
            sel.dataset.prevValue = data.status;
            sel.dataset.status = data.status;
          }

          // detail의 변경일자 텍스트 갱신
          if (data.status_updated_at && statusUpdatedAtText) {
            statusUpdatedAtText.textContent = data.status_updated_at;
          }

          showAlert(alertHost, data.message || "변경되었습니다.", "success");

          // 공식 onSuccess
          if (onSuccess) {
            try {
              onSuccess(data, { sel, form, actionType, updateUrl });
            } catch {
              /* ignore */
            }
          }
        } catch (err) {
          sel.value = prev;
          sel.dataset.prevValue = prev;
          sel.dataset.status = prev;
          showAlert(alertHost, err?.message || "변경 실패", "danger");
        } finally {
          setBusy(sel, false);
          form.dataset.submitting = "0";
        }
      });
    };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bind, { once: true });
    } else {
      bind();
    }
  };
})();
