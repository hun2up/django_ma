// django_ma/static/js/manual/manual_list_edit.js
// --------------------------------------------------
// ✅ Manual List Edit Mode (FINAL - Refactor)
// - superuser 전용 목록 편집모드: 드래그 정렬 + 삭제 + (타이틀/공개범위) 일괄 수정 저장
// - "편집모드가 아닐 때"는 상세페이지 링크 이동이 반드시 정상 동작
// - SortableJS 미로드 시 안전 종료 + 콘솔 에러
// - CSRF: hidden form(#manualEditCsrfForm)에서 읽음 (CSRF_COOKIE_HTTPONLY 대응)
// - 링크 복원 안정화: a.dataset.href(또는 data-href) 기반으로 확정 복구
// - 이벤트 위임 1회 바인딩 + 중복 바인딩 방지
// --------------------------------------------------

(() => {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[manual_list_edit]", ...a);

  /* -----------------------------
   * DOM / Boot
   * ----------------------------- */
  const boot = window.ManualListBoot || {};
  const listEl = document.getElementById("manualListGroup");
  const btnEdit = document.getElementById("btnManualEditMode");
  const btnSave = document.getElementById("btnManualSaveOrder");
  const btnDone = document.getElementById("btnManualDone");
  const csrfForm = document.getElementById("manualEditCsrfForm");

  if (!listEl || !btnEdit || !btnSave || !btnDone || !csrfForm) return;

  // ✅ 중복 바인딩 방지
  if (listEl.dataset.bound === "true") return;
  listEl.dataset.bound = "true";

  // ✅ SortableJS 로드 확인
  if (typeof window.Sortable === "undefined") {
    console.error("[manual_list_edit] SortableJS not loaded. (Sortable.min.js 포함 확인)");
    return;
  }

  /* -----------------------------
   * helpers
   * ----------------------------- */
  const toStr = (v) => String(v ?? "").trim();
  const isDigits = (v) => /^\d+$/.test(String(v ?? ""));
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const reorderUrl = toStr(boot.reorderUrl);
  const deleteUrl = toStr(boot.deleteUrl);
  const bulkUpdateUrl = toStr(boot.bulkUpdateUrl);

  function getCSRFToken() {
    const el = csrfForm.querySelector('input[name="csrfmiddlewaretoken"]');
    return toStr(el?.value);
  }
  const csrfToken = getCSRFToken();

  function alertBox(msg) {
    window.alert(toStr(msg) || "오류가 발생했습니다.");
  }

  function setBtnLoading(btn, isLoading, loadingText) {
    if (!btn) return;
    if (isLoading) {
      if (btn.dataset.oldText == null) btn.dataset.oldText = btn.textContent || "";
      btn.disabled = true;
      if (loadingText) btn.textContent = loadingText;
    } else {
      btn.disabled = false;
      if (btn.dataset.oldText != null) btn.textContent = btn.dataset.oldText;
      delete btn.dataset.oldText;
    }
  }

  async function safeReadJson(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      const text = await res.text().catch(() => "");
      return { __non_json__: true, __text__: text };
    }
    return await res.json().catch(() => ({}));
  }

  async function postJson(url, bodyObj) {
    if (!url) throw new Error("요청 URL이 비어있습니다.");
    if (!csrfToken) throw new Error("CSRF 토큰이 없습니다. (manualEditCsrfForm 확인)");
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(bodyObj || {}),
    });

    const data = await safeReadJson(res);
    if (data?.__non_json__) throw new Error(`요청 실패 (HTTP ${res.status})`);
    if (!res.ok || !data?.ok) throw new Error(data?.message || `요청 실패 (HTTP ${res.status})`);
    return data;
  }

  /* -----------------------------
   * core selectors
   * ----------------------------- */
  function getItems() {
    return qsa("a.manual-item", listEl);
  }

  function getOrderedIds() {
    return getItems().map((a) => a.dataset.id).filter(isDigits);
  }

  /* -----------------------------
   * link block/restore (fix: 상세 이동 정상화)
   * - 템플릿에 data-href를 넣어두면 가장 안정적
   * - 없더라도 최초 href를 dataset.href로 저장해 복원
   * ----------------------------- */
  function getOriginalHref(a) {
    // data-href 우선, 없으면 dataset.href, 그 다음 현재 href
    return toStr(a.dataset.href || a.getAttribute("data-href") || a.getAttribute("href") || "#");
  }

  function blockOrRestoreLinks(isBlock) {
    getItems().forEach((a) => {
      const original = getOriginalHref(a);

      if (isBlock) {
        // 편집모드: 원래 링크를 반드시 dataset.href로 보관
        a.dataset.href = original;
        a.setAttribute("href", "javascript:void(0)");
      } else {
        // 일반모드: 원래 링크로 확정 복구
        a.setAttribute("href", original);
      }
    });
  }

  /* -----------------------------
   * editors (title/access)
   * ----------------------------- */
  function syncAccessSelect(a) {
    const sel = a.querySelector(".manual-access-select");
    if (!sel) return;
    const access = toStr(a.dataset.access || "normal");
    sel.value = ["normal", "admin", "staff"].includes(access) ? access : "normal";
  }

  function toggleEditors(isEdit) {
    getItems().forEach((a) => {
      const textEl = a.querySelector(".manual-title-text");
      const inputEl = a.querySelector(".manual-title-input");
      const accessSel = a.querySelector(".manual-access-select");

      // 타이틀 에디터
      if (textEl && inputEl) {
        if (isEdit) {
          inputEl.value = toStr(textEl.textContent);
          textEl.classList.add("d-none");
          inputEl.classList.remove("d-none");
        } else {
          textEl.classList.remove("d-none");
          inputEl.classList.add("d-none");
        }
      }

      // 공개범위 select
      if (accessSel) {
        if (isEdit) {
          syncAccessSelect(a);
          accessSel.classList.remove("d-none");
        } else {
          accessSel.classList.add("d-none");
        }
      }

      // 배지(관리자전용/직원전용)는 편집모드에서 숨김
      qsa(".manual-badge-admin, .manual-badge-staff", a).forEach((b) => {
        b.classList.toggle("d-none", isEdit);
      });
    });
  }

  /* -----------------------------
   * Sortable
   * ----------------------------- */
  let sortable = null;
  let isEditMode = false;

  function enableSortable() {
    if (sortable) return;
    sortable = new Sortable(listEl, {
      animation: 150,
      handle: ".manual-drag-handle",
      draggable: "a.manual-item",
      ghostClass: "sortable-ghost",
    });
  }

  function disableSortable() {
    if (!sortable) return;
    sortable.destroy();
    sortable = null;
  }

  function setEditUI(nextEdit) {
    isEditMode = !!nextEdit;

    // 핸들/삭제 버튼 토글
    qsa(".manual-drag-handle", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));
    qsa(".btn-manual-delete", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));

    // 링크 이동 차단/복원 (핵심)
    blockOrRestoreLinks(isEditMode);

    // 타이틀/공개범위 에디터 토글
    toggleEditors(isEditMode);

    // 상단 버튼 토글
    btnEdit.classList.toggle("d-none", isEditMode);
    btnSave.classList.toggle("d-none", !isEditMode);
    btnDone.classList.toggle("d-none", !isEditMode);

    log("setEditUI", { isEditMode });
  }

  /* -----------------------------
   * collect changes
   * ----------------------------- */
  function collectMetaChanges() {
    const items = [];

    getItems().forEach((a) => {
      const id = a.dataset.id;
      if (!isDigits(id)) return;

      const textEl = a.querySelector(".manual-title-text");
      const inputEl = a.querySelector(".manual-title-input");
      const accessSel = a.querySelector(".manual-access-select");

      const oldTitle = toStr(textEl?.textContent);
      const newTitle = toStr(inputEl?.value);
      const oldAccess = toStr(a.dataset.access || "normal");
      const newAccess = toStr(accessSel?.value || oldAccess);

      if (!newTitle) throw new Error("제목은 비워둘 수 없습니다.");
      if (newTitle.length > 80) throw new Error("제목은 80자 이하여야 합니다.");
      if (!["normal", "admin", "staff"].includes(newAccess)) throw new Error("공개 범위 값이 올바르지 않습니다.");

      // 변경된 것만 수집
      if (newTitle !== oldTitle || newAccess !== oldAccess) {
        items.push({ id: Number(id), title: newTitle, access: newAccess });
      }
    });

    return items;
  }

  function applyServerUpdated(data) {
    // 서버 반영값으로 화면/데이터 동기화
    (data?.updated || []).forEach((u) => {
      const a = listEl.querySelector(`a.manual-item[data-id="${u.id}"]`);
      if (!a) return;

      const textEl = a.querySelector(".manual-title-text");
      const inputEl = a.querySelector(".manual-title-input");
      if (textEl) textEl.textContent = u.title;
      if (inputEl) inputEl.value = u.title;

      const access = u.admin_only ? "admin" : (u.is_published ? "normal" : "staff");
      a.dataset.access = access;

      const sel = a.querySelector(".manual-access-select");
      if (sel) sel.value = access;
    });
  }

  /* -----------------------------
   * save all
   * ----------------------------- */
  async function saveAll() {
    try {
      setBtnLoading(btnSave, true, "저장중...");

      // 1) 타이틀 + 공개범위 저장(변경된 항목만)
      const metaItems = collectMetaChanges();
      if (metaItems.length > 0) {
        const data = await postJson(bulkUpdateUrl, { items: metaItems });
        applyServerUpdated(data);
      }

      // 2) 순서 저장
      const ordered_ids = getOrderedIds();
      await postJson(reorderUrl, { ordered_ids });

      alertBox("저장되었습니다.");
    } catch (e) {
      console.error("[manual_list_edit] saveAll error", e);
      alertBox(e?.message || "저장 중 오류가 발생했습니다.");
    } finally {
      setBtnLoading(btnSave, false);
    }
  }

  /* -----------------------------
   * events
   * ----------------------------- */
  btnEdit.addEventListener("click", () => {
    setEditUI(true);
    enableSortable();
  });

  btnDone.addEventListener("click", () => {
    disableSortable();
    setEditUI(false);
  });

  btnSave.addEventListener("click", saveAll);

  // 삭제 (이벤트 위임)
  listEl.addEventListener("click", async (e) => {
    const btn = e.target?.closest?.(".btn-manual-delete");
    if (!btn || !isEditMode) return;

    const item = btn.closest("a.manual-item");
    const id = item?.dataset?.id;
    if (!isDigits(id)) return;

    e.preventDefault();
    e.stopPropagation();

    if (!confirm("정말 삭제하시겠습니까?")) return;

    try {
      btn.disabled = true;
      await postJson(deleteUrl, { id: Number(id) });
      item.remove();
    } catch (err) {
      console.error("[manual_list_edit] delete error", err);
      alertBox(err?.message || "삭제 중 오류가 발생했습니다.");
      btn.disabled = false;
    }
  });

  // ✅ 편집모드에서만 “클릭 이동” 막기 (일반모드에서는 절대 막지 않음)
  listEl.addEventListener("click", (e) => {
    if (!isEditMode) return;

    // 편집모드에서도 input/select/버튼/핸들 클릭은 허용
    if (e.target.closest("input, select, button, textarea, .manual-drag-handle")) return;

    const a = e.target.closest("a.manual-item");
    if (a) {
      e.preventDefault();
      e.stopPropagation();
    }
  });

  /* -----------------------------
   * init
   * ----------------------------- */
  // 초기 상태: 일반모드에서 링크는 반드시 원래대로 유지
  setEditUI(false);
})();
