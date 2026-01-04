// django_ma/static/js/board/common/detail_inline_update.js
//
// Board Common Inline Update (DETAIL)
// - post_detail / task_detail 공용
// - superuser 담당자/상태 select 변경 AJAX
// - detail 화면의 #statusUpdatedAtText 갱신
// - status select 옵션 data-color 기반 스타일 적용

(function () {
  "use strict";

  const Board = (window.Board = window.Board || {});
  Board.Common = Board.Common || {};

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
    if (busy) {
      selectEl.style.pointerEvents = "none";
      selectEl.style.opacity = "0.7";
    } else {
      selectEl.style.pointerEvents = "";
      selectEl.style.opacity = "";
    }
  }

  function showAlert(alertHost, message, type = "success") {
    if (!alertHost) return window.alert(message);
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

  function applyStatusColor(selectEl) {
    if (!(selectEl instanceof HTMLSelectElement)) return;
    const opt = selectEl.options[selectEl.selectedIndex];
    const color = opt?.getAttribute("data-color");
    if (!color) return;
    selectEl.style.color = color;
    selectEl.style.fontWeight = "600";
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

  /**
   * initDetailInlineUpdate
   * @param {Object} opts
   * @param {string} opts.bootId - "postDetailBoot" | "taskDetailBoot"
   */
  Board.Common.initDetailInlineUpdate = function initDetailInlineUpdate(opts) {
    const bootId = opts?.bootId;
    if (!bootId) return;

    const bind = () => {
      const boot = document.getElementById(bootId);
      const updateUrl = boot?.dataset?.updateUrl || "";
      if (!updateUrl) return; // 일반유저 페이지에서도 안전 종료

      const alertHost = document.getElementById("inlineUpdateAlertHost");
      const statusUpdatedAtText = document.getElementById("statusUpdatedAtText");

      // 초기: status 색상
      document.querySelectorAll("select.status-select").forEach(applyStatusColor);

      // 초기 prevValue
      document
        .querySelectorAll(
          "form.inline-update-form select[name='handler'], form.inline-update-form select[name='status']"
        )
        .forEach((s) => (s.dataset.prevValue = s.value));

      // 이벤트 위임
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

          if (actionType === "status") applyStatusColor(sel);

          if (data.status_updated_at && statusUpdatedAtText) {
            statusUpdatedAtText.textContent = data.status_updated_at;
          }

          showAlert(alertHost, data.message || "변경되었습니다.", "success");
        } catch (err) {
          sel.value = prev;
          if (actionType === "status") applyStatusColor(sel);
          showAlert(alertHost, err?.message || "변경 실패", "danger");
        } finally {
          setBusy(sel, false);
          form.dataset.submitting = "0";
        }
      });
    };

    // ✅ 언제 로드되든 안전하게 바인딩
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bind, { once: true });
    } else {
      bind();
    }
  };
})();
