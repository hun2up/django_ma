// django_ma/static/js/board/common/inline_update.js
// =========================================================
// Board Common Inline Update (LIST) - FINAL
// - post_list / task_list 공용
// - handler/status select 인라인 변경 AJAX
// - status_updated_at(td.status-updated-at) 갱신
// - ✅ onSuccess 공식 지원: onSuccess(data, ctx)
//
// ✅ ctx 제공:
// { fieldName, actionType, idKey, idValue, selectEl, form, updateUrl }
//
// 전제(템플릿):
// - boot div: #postListBoot or #taskListBoot with data-update-url
// - inline form: form.inline-update-form
//   - hidden: action_type
//   - hidden: post_id or task_id
//   - select[name=handler], select[name=status].status-select
// - td.status-updated-at 있으면 갱신
// =========================================================

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
    selectEl.style.pointerEvents = busy ? "none" : "";
    selectEl.style.opacity = busy ? "0.7" : "";
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

  async function sendUpdate({ updateUrl, form, idKey, idValue, actionType, value }) {
    if (!updateUrl) throw new Error("AJAX update URL이 없습니다. (boot data-update-url 확인)");

    const csrf = getCsrfFromForm(form);
    if (!csrf) throw new Error("CSRF 토큰을 폼에서 찾을 수 없습니다.");

    const body = new URLSearchParams();
    body.set(idKey, idValue);
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
   * initListInlineUpdate
   * @param {Object} opts
   * @param {string} opts.bootId  - "postListBoot" | "taskListBoot"
   * @param {string} opts.idKey   - "post_id" | "task_id"
   * @param {(data:Object, ctx:Object)=>void} [opts.onSuccess]
   */
  Board.Common.initListInlineUpdate = function initListInlineUpdate(opts) {
    const bootId = opts?.bootId;
    const idKey = opts?.idKey;
    const onSuccess = typeof opts?.onSuccess === "function" ? opts.onSuccess : null;

    if (!bootId || !idKey) return;

    const bind = () => {
      const boot = document.getElementById(bootId);
      const updateUrl = boot?.dataset?.updateUrl || "";
      if (!updateUrl) return; // non-superuser 화면/잘못된 템플릿에서도 안전 종료

      const alertHost = document.getElementById("inlineUpdateAlertHost");

      // 초기 prevValue 세팅
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

        const fieldName = sel.getAttribute("name");
        if (fieldName !== "handler" && fieldName !== "status") return;

        const idValue = qs(`input[name="${idKey}"]`, form)?.value || "";
        const actionType = qs('input[name="action_type"]', form)?.value || "";

        if (!idValue || !actionType) {
          showAlert(alertHost, `필수값(${idKey}/action_type)이 없습니다.`, "danger");
          return;
        }

        if (form.dataset.submitting === "1") return;
        form.dataset.submitting = "1";

        const prev = sel.dataset.prevValue ?? sel.value;
        sel.dataset.prevValue = sel.value;

        setBusy(sel, true);

        try {
          const data = await sendUpdate({
            updateUrl,
            form,
            idKey,
            idValue,
            actionType,
            value: sel.value,
          });

          // 상태변경일 갱신
          if (data.status_updated_at) {
            const tr = sel.closest("tr");
            const td = tr?.querySelector("td.status-updated-at");
            if (td) td.textContent = data.status_updated_at;
          }

          // 서버가 status를 돌려주면 확정 동기화
          if (fieldName === "status") {
            const confirmed = data.status || sel.value;
            sel.value = confirmed;
            sel.dataset.prevValue = confirmed;
            sel.dataset.status = confirmed; // status_ui에서 사용
          }

          showAlert(alertHost, data.message || "변경되었습니다.", "success");

          // ✅ 공식 onSuccess
          if (onSuccess) {
            onSuccess(data, {
              fieldName,
              actionType,
              idKey,
              idValue,
              selectEl: sel,
              form,
              updateUrl,
            });
          }
        } catch (err) {
          sel.value = prev;
          sel.dataset.prevValue = prev;
          if (fieldName === "status") sel.dataset.status = prev;

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
