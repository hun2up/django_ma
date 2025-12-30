// django_ma/static/js/post_list.js

(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    const boot = document.getElementById("postListBoot");
    const updateUrl = boot?.dataset?.updateUrl || "";
    const alertHost = document.getElementById("inlineUpdateAlertHost");

    console.log("[post_list.js] init", { updateUrl, hasBoot: !!boot, hasAlertHost: !!alertHost });

    const qs = (sel, root = document) => root.querySelector(sel);

    function escapeHtml(str) {
      return String(str ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function showAlert(message, type = "success") {
      if (!alertHost) return window.alert(message);
      alertHost.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show text-center" role="alert">
          ${escapeHtml(message)}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      `;
      setTimeout(() => {
        const el = qs(".alert", alertHost);
        if (!el) return;
        try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch { el.remove(); }
      }, 2500);
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

    async function safeJson(res) {
      try { return await res.json(); } catch { return null; }
    }

    function getCsrfFromForm(form) {
      // ✅ 쿠키 대신 form 내부 hidden input 사용 (secure cookie 이슈 회피)
      return form?.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";
    }

    async function postUpdate({ form, postId, actionType, value }) {
      if (!updateUrl) throw new Error("AJAX update URL이 없습니다. (postListBoot data-update-url 확인)");

      const csrf = getCsrfFromForm(form);
      if (!csrf) throw new Error("CSRF 토큰을 폼에서 찾을 수 없습니다.");

      const body = new URLSearchParams();
      body.set("post_id", postId);
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

    document.addEventListener("change", async (e) => {
      const sel = e.target;
      if (!(sel instanceof HTMLSelectElement)) return;

      const form = sel.closest("form.inline-update-form");
      if (!form) return;

      const fieldName = sel.getAttribute("name");
      if (fieldName !== "handler" && fieldName !== "status") return; // 검색필터 select 제외

      const postId = qs('input[name="post_id"]', form)?.value || "";
      const actionType = qs('input[name="action_type"]', form)?.value || "";

      if (!postId || !actionType) {
        showAlert("필수값(post_id/action_type)이 없습니다.", "danger");
        return;
      }

      if (form.dataset.submitting === "1") return;
      form.dataset.submitting = "1";

      const prev = sel.dataset.prevValue ?? sel.value;
      sel.dataset.prevValue = sel.value;

      setBusy(sel, true);

      try {
        const data = await postUpdate({ form, postId, actionType, value: sel.value });

        // 상태변경일 갱신
        if (data.status_updated_at) {
          const tr = sel.closest("tr");
          const td = tr?.querySelector("td.status-updated-at");
          if (td) td.textContent = data.status_updated_at;
        }

        showAlert(data.message || "변경되었습니다.", "success");
      } catch (err) {
        sel.value = prev;
        showAlert(err?.message || "변경 실패", "danger");
      } finally {
        setBusy(sel, false);
        form.dataset.submitting = "0";
      }
    });

    // 초기 prevValue 세팅
    document
      .querySelectorAll("form.inline-update-form select[name='handler'], form.inline-update-form select[name='status']")
      .forEach((s) => (s.dataset.prevValue = s.value));
  });
})();
