/**
 * django_ma/static/js/post_detail.js
 * 게시글 상세 페이지 기능 스크립트
 * - 댓글 수정 기능 (인라인 편집)
 * - ✅ superuser 담당자/상태 드롭다운 변경 즉시 반영(AJAX) + 상단 안내메시지
 *
 * 전제(템플릿):
 * - <div id="postDetailBoot" data-update-url="..."></div>
 * - <div id="inlineUpdateAlertHost"></div>
 * - 담당자/상태 폼: form.inline-update-form 내부에
 *   - input[name="csrfmiddlewaretoken"]
 *   - input[name="action_type"] (handler|status)
 *   - select[name="handler"] or select[name="status"]
 * - 상태변경일 표시: <span id="statusUpdatedAtText">...</span>
 */

document.addEventListener("DOMContentLoaded", () => {
  // =========================================================
  // 1) 댓글 수정 기능 (기존 로직 유지)
  // =========================================================
  const editButtons = document.querySelectorAll(".edit-comment-btn");

  editButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const commentId = btn.dataset.id;
      const container = btn.closest(".comment-content");
      const textP = container.querySelector("p");
      const oldText = (textP?.innerText || "").trim();

      // 수정버튼 숨김
      const actionBtns = container.querySelector(".edit-delete-btns");
      if (actionBtns) actionBtns.style.display = "none";

      // 폼 생성
      textP.outerHTML = `
        <form method="post" class="d-flex align-items-center gap-1 w-100">
          <input type="hidden" name="action_type" value="edit_comment">
          <input type="hidden" name="comment_id" value="${commentId}">
          <textarea name="content" class="form-control form-control-sm flex-grow-1" rows="1">${oldText}</textarea>
          <button type="submit" class="btn btn-sm btn-primary px-2 py-1" style="font-size:12px;">저장</button>
          <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-1 cancel-edit" style="font-size:12px;">취소</button>
        </form>
      `;

      // 취소 시 새로고침
      const cancelBtn = container.querySelector(".cancel-edit");
      if (cancelBtn) cancelBtn.addEventListener("click", () => window.location.reload());
    });
  });

  // =========================================================
  // 2) ✅ superuser 인라인 업데이트(AJAX) - 담당자/상태
  // =========================================================
  const boot = document.getElementById("postDetailBoot");
  const updateUrl = boot?.dataset?.updateUrl || "";
  const alertHost = document.getElementById("inlineUpdateAlertHost");
  const statusUpdatedAtText = document.getElementById("statusUpdatedAtText");

  // updateUrl이 없으면(일반 사용자거나 템플릿 주입 누락) 조용히 종료
  if (!updateUrl) {
    // console.log("[post_detail.js] inline update disabled (no updateUrl)");
    return;
  }

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

  // 초기: 상태 select 색상 적용(옵션에 data-color가 있을 때만)
  document.querySelectorAll("select.status-select").forEach((sel) => applyStatusColor(sel));

  // 이벤트 위임: 상세 인라인 폼 select 변경
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

    // 중복 요청 방지
    if (form.dataset.submitting === "1") return;
    form.dataset.submitting = "1";

    // 롤백용 이전값
    const prev = sel.dataset.prevValue ?? sel.value;
    sel.dataset.prevValue = sel.value;

    setBusy(sel, true);

    try {
      const data = await postUpdate({ form, actionType, value: sel.value });

      if (actionType === "status") applyStatusColor(sel);

      // 상태변경일 즉시 갱신
      if (data.status_updated_at && statusUpdatedAtText) {
        statusUpdatedAtText.textContent = data.status_updated_at;
      }

      showAlert(data.message || "변경되었습니다.", "success");
    } catch (err) {
      // 실패 시 원복
      sel.value = prev;
      if (actionType === "status") applyStatusColor(sel);
      showAlert(err?.message || "변경 실패", "danger");
    } finally {
      setBusy(sel, false);
      form.dataset.submitting = "0";
    }
  });

  // 초기 prevValue 세팅
  document
    .querySelectorAll(
      "form.inline-update-form select[name='handler'], form.inline-update-form select[name='status']"
    )
    .forEach((s) => {
      s.dataset.prevValue = s.value;
    });
});
