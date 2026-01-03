/**
 * django_ma/static/js/post_detail.js
 * - 댓글 수정 기능(인라인 편집) 개선:
 *   1) textarea rows 기본 7줄
 *   2) 버튼 줄바꿈 방지(폼 flex-nowrap + textarea 폭 제한)
 *   3) ✅ 동적 폼에 CSRF 토큰 삽입(403 CSRF missing 해결)
 *   4) 취소 시 새로고침 대신 원복
 *
 * - superuser 담당자/상태 드롭다운 변경 즉시 반영(AJAX) 유지
 */

document.addEventListener("DOMContentLoaded", () => {
  const qs = (sel, root = document) => root.querySelector(sel);

  /* =========================================================
   * 1) 댓글 수정 기능 (FIX + UX 개선)
   * ========================================================= */

  function escapeForTextarea(str) {
    // textarea 내부에 안전하게 넣기 위한 최소 escape
    // (특히 </textarea> 같은 케이스 방지)
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function getEditCsrfToken() {
    // 템플릿에 추가한 hidden input 우선
    const v = qs("#commentEditCsrfToken")?.value;
    if (v && v !== "NOTPROVIDED") return v;

    // fallback: 페이지 내 다른 폼의 csrf 토큰에서 가져오기
    return qs("input[name='csrfmiddlewaretoken']")?.value || "";
  }

  function closeEditMode(container, restoredText) {
    const form = qs("form.comment-edit-form", container);
    if (form) form.remove();

    const p = document.createElement("p");
    p.className = "mb-0 small comment-text";
    p.style.whiteSpace = "pre-wrap";
    p.textContent = restoredText ?? "";
    container.insertBefore(p, container.firstChild);

    const actionBtns = qs(".edit-delete-btns", container);
    if (actionBtns) actionBtns.style.display = "";
  }

  document.querySelectorAll(".edit-comment-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const commentId = btn.dataset.id;
      const container = btn.closest(".comment-content");
      if (!container) return;

      // 이미 수정모드면 중복 생성 방지
      if (container.dataset.editing === "1") return;
      container.dataset.editing = "1";

      const textP = qs("p.comment-text", container) || qs("p", container);
      const oldText = (textP?.innerText || "").trim();

      // 수정버튼 숨김
      const actionBtns = qs(".edit-delete-btns", container);
      if (actionBtns) actionBtns.style.display = "none";

      // 원문 p 제거
      if (textP) textP.remove();

      const csrf = getEditCsrfToken();
      if (!csrf) {
        // CSRF가 없으면 저장이 절대 안 되므로 안내 후 복구
        alert("CSRF 토큰을 찾지 못했습니다. 페이지를 새로고침 후 다시 시도해주세요.");
        container.dataset.editing = "0";
        if (actionBtns) actionBtns.style.display = "";
        return;
      }

      // ✅ 수정 폼 삽입 (rows=7 / flex-nowrap / textarea 폭 제한)
      const form = document.createElement("form");
      form.method = "post";
      form.className = "comment-edit-form comment-edit-form-js"; // css는 템플릿에 있음
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
        <input type="hidden" name="action_type" value="edit_comment">
        <input type="hidden" name="comment_id" value="${commentId}">
        <textarea name="content"
                  class="form-control form-control-sm comment-edit-textarea"
                  rows="7">${escapeForTextarea(oldText)}</textarea>
        <div class="comment-edit-actions">
          <button type="submit" class="btn btn-sm btn-primary px-2 py-1" style="font-size:12px;">저장</button>
          <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-1 cancel-edit" style="font-size:12px;">취소</button>
        </div>
      `;
      container.insertBefore(form, container.firstChild);

      // 취소 시: 원복
      const cancelBtn = qs(".cancel-edit", form);
      if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
          container.dataset.editing = "0";
          closeEditMode(container, oldText);
        });
      }

      // 저장 후에는 서버에서 리다이렉트/렌더가 일어나므로 별도 처리 불필요
      // (원하면 fetch로 바꿔서 무새로고침 저장도 가능)
    });
  });

  /* =========================================================
   * 2) ✅ superuser 인라인 업데이트(AJAX) - 담당자/상태
   * ========================================================= */
  const boot = document.getElementById("postDetailBoot");
  const updateUrl = boot?.dataset?.updateUrl || "";
  const alertHost = document.getElementById("inlineUpdateAlertHost");
  const statusUpdatedAtText = document.getElementById("statusUpdatedAtText");

  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function showAlert(message, type = "success") {
    if (!alertHost) {
      window.alert(message);
      return;
    }
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

  function getCsrfFromForm(form) {
    return form?.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";
  }

  async function safeJson(res) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }

  function applyStatusColor(selectEl) {
    if (!(selectEl instanceof HTMLSelectElement)) return;
    const opt = selectEl.options[selectEl.selectedIndex];
    const color = opt?.getAttribute("data-color");
    if (!color) return;
    selectEl.style.color = color;
    selectEl.style.fontWeight = "600";
  }

  async function postUpdate({ form, actionType, value }) {
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

  // updateUrl이 있을 때만(슈퍼유저 상세 인라인 기능) 바인딩
  if (updateUrl) {
    // 초기: 상태 select 색상 적용
    document.querySelectorAll("select.status-select").forEach((sel) => applyStatusColor(sel));

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

      const name = sel.getAttribute("name");
      if (name !== "handler" && name !== "status") return;

      const actionType = qs("input[name='action_type']", form)?.value || "";
      if (!actionType) {
        showAlert("action_type이 없습니다.", "danger");
        return;
      }

      if (form.dataset.submitting === "1") return;
      form.dataset.submitting = "1";

      const prev = sel.dataset.prevValue ?? sel.value;
      sel.dataset.prevValue = sel.value;

      setBusy(sel, true);

      try {
        const data = await postUpdate({ form, actionType, value: sel.value });

        if (actionType === "status") applyStatusColor(sel);

        if (data.status_updated_at && statusUpdatedAtText) {
          statusUpdatedAtText.textContent = data.status_updated_at;
        }

        showAlert(data.message || "변경되었습니다.", "success");
      } catch (err) {
        sel.value = prev;
        if (actionType === "status") applyStatusColor(sel);
        showAlert(err?.message || "변경 실패", "danger");
      } finally {
        setBusy(sel, false);
        form.dataset.submitting = "0";
      }
    });
  }
});
