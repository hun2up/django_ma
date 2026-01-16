// django_ma/static/js/manual/manual_list_edit.js
// -----------------------------------------------------------------------------
// Manual List Edit Mode (FINAL - Refactor)
// - superuser 전용 목록 편집모드: 드래그 정렬 + 삭제 + (타이틀/공개범위) 일괄 수정 저장
// - 편집모드가 아닐 때 링크 이동은 반드시 정상 동작
// - SortableJS 미로드 시 안전 종료
// - CSRF: hidden form(#manualEditCsrfForm)에서 읽음
// - 이벤트 위임 1회 + 중복 바인딩 방지
// -----------------------------------------------------------------------------

(() => {
  const S = window.ManualShared;
  if (!S) {
    console.error("[manual_list_edit] ManualShared not loaded. (_shared.js 포함 확인)");
    return;
  }

  const {
    toStr,
    isDigits,
    getCSRFTokenFromForm,
    setBtnLoading,
    postJson,
  } = S;

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

  // 중복 바인딩 방지
  if (listEl.dataset.bound === "true") return;
  listEl.dataset.bound = "true";

  // SortableJS 로드 확인
  if (typeof window.Sortable === "undefined") {
    console.error("[manual_list_edit] SortableJS not loaded. (Sortable.min.js 포함 확인)");
    return;
  }

  const csrfToken = getCSRFTokenFromForm(csrfForm);

  const reorderUrl = toStr(boot.reorderUrl);
  const deleteUrl = toStr(boot.deleteUrl);
  const bulkUpdateUrl = toStr(boot.bulkUpdateUrl);

  const api = {
    json: (url, body) => postJson(url, body, csrfToken),
  };

  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function alertBox(msg) {
    window.alert(toStr(msg) || "오류가 발생했습니다.");
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
   * link block/restore
   * - data-href 우선. 없으면 최초 href를 dataset.href로 저장해 복원
   * ----------------------------- */
  function getOriginalHref(a) {
    return toStr(a.dataset.href || a.getAttribute("data-href") || a.getAttribute("href") || "#");
  }

  function blockOrRestoreLinks(isBlock) {
    getItems().forEach((a) => {
      const original = getOriginalHref(a);
      if (isBlock) {
        a.dataset.href = original;
        a.setAttribute("href", "javascript:void(0)");
      } else {
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

    // 링크 이동 차단/복원(핵심)
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

      if (newTitle !== oldTitle || newAccess !== oldAccess) {
        items.push({ id: Number(id), title: newTitle, access: newAccess });
      }
    });

    return items;
  }

  function applyServerUpdated(data) {
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
        const data = await api.json(bulkUpdateUrl, { items: metaItems });
        applyServerUpdated(data);
      }

      // 2) 순서 저장
      const ordered_ids = getOrderedIds();
      await api.json(reorderUrl, { ordered_ids });

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

  // 삭제(이벤트 위임)
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
      await api.json(deleteUrl, { id: Number(id) });
      item.remove();
    } catch (err) {
      console.error("[manual_list_edit] delete error", err);
      alertBox(err?.message || "삭제 중 오류가 발생했습니다.");
      btn.disabled = false;
    }
  });

  // 편집모드에서만 클릭 이동 막기(일반모드에서는 절대 막지 않음)
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
  setEditUI(false);
})();
