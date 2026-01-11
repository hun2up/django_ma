// django_ma/static/js/manual/manual_list_edit.js
// --------------------------------------------------
// ✅ Manual List Edit Mode (FINAL - Refactor)
// - superuser 전용 편집모드: 드래그 정렬 + 삭제 + 순서 저장 + 완료
// - SortableJS 미로드 시 안전 종료 + 콘솔 에러
// - CSRF: hidden form(#manualEditCsrfForm)에서 읽음 (CSRF_COOKIE_HTTPONLY 대응)
// - 링크 이동 차단/복원: href를 data-href로 보관
// - 실패 시 사용자 메시지 + 버튼 상태 복구
// --------------------------------------------------

(() => {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[manual_list_edit]", ...a);

  /* -----------------------------
   * helpers
   * ----------------------------- */
  const toStr = (v) => String(v ?? "").trim();
  const isDigits = (v) => /^\d+$/.test(String(v ?? ""));
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function alertBox(msg) {
    window.alert(toStr(msg) || "오류가 발생했습니다.");
  }

  function setBtnLoading(btn, isLoading, loadingText) {
    if (!btn) return;
    if (isLoading) {
      if (!btn.dataset.oldText) btn.dataset.oldText = btn.textContent || "";
      btn.disabled = true;
      if (loadingText) btn.textContent = loadingText;
    } else {
      btn.disabled = false;
      if (btn.dataset.oldText !== undefined) btn.textContent = btn.dataset.oldText;
      delete btn.dataset.oldText;
    }
  }

  function getCSRFToken(csrfForm) {
    const el = csrfForm?.querySelector?.('input[name="csrfmiddlewaretoken"]');
    return toStr(el?.value);
  }

  async function safeReadJson(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      const text = await res.text().catch(() => "");
      return { __non_json__: true, __text__: text };
    }
    return await res.json().catch(() => ({}));
  }

  async function postJson(url, bodyObj, csrfToken) {
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

    if (data?.__non_json__) {
      throw new Error(`요청 실패 (HTTP ${res.status})`);
    }
    if (!res.ok || !data?.ok) {
      throw new Error(data?.message || `요청 실패 (HTTP ${res.status})`);
    }
    return data;
  }

  /* -----------------------------
   * dom + boot
   * ----------------------------- */
  const boot = window.ManualListBoot || {};
  const listEl = document.getElementById("manualListGroup");
  const btnEdit = document.getElementById("btnManualEditMode");
  const btnSave = document.getElementById("btnManualSaveOrder");
  const btnDone = document.getElementById("btnManualDone");
  const csrfForm = document.getElementById("manualEditCsrfForm");

  // 필수 요소가 없으면 조용히 종료
  if (!listEl || !btnEdit || !btnSave || !btnDone || !csrfForm) return;

  // SortableJS 로드 확인
  if (typeof window.Sortable === "undefined") {
    console.error("[manual_list_edit] SortableJS not loaded. (Sortable.min.js 포함 확인)");
    return;
  }

  const reorderUrl = toStr(boot.reorderUrl);
  const deleteUrl = toStr(boot.deleteUrl);

  if (!reorderUrl || !deleteUrl) {
    console.error("[manual_list_edit] Boot URLs missing.", { reorderUrl, deleteUrl });
    return;
  }

  const csrfToken = getCSRFToken(csrfForm);
  if (!csrfToken) {
    console.error("[manual_list_edit] CSRF token missing. (manualEditCsrfForm에 {% csrf_token %} 확인)");
    return;
  }

  /* -----------------------------
   * state
   * ----------------------------- */
  let isEditMode = false;
  let sortable = null;

  function getItems() {
    return qsa("a.manual-item", listEl);
  }

  function getOrderedIds() {
    return getItems()
      .map((a) => a?.dataset?.id)
      .filter((x) => isDigits(x));
  }

  function blockOrRestoreLinks(enableBlock) {
    // enableBlock=true => 링크 이동 차단
    getItems().forEach((a) => {
      if (enableBlock) {
        if (!a.dataset.href) a.dataset.href = a.getAttribute("href") || "";
        a.setAttribute("href", "javascript:void(0)");
      } else {
        const original = a.dataset.href || a.getAttribute("href") || "#";
        a.setAttribute("href", original);
      }
    });
  }

  function setEditUI(nextEdit) {
    isEditMode = !!nextEdit;

    // 핸들/삭제 버튼 토글
    qsa(".manual-drag-handle", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));
    qsa(".btn-manual-delete", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));

    // 링크 이동 차단/복원
    blockOrRestoreLinks(isEditMode);

    // 항목 스타일 토글
    getItems().forEach((a) => a.classList.toggle("manual-editing", isEditMode));

    // 상단 버튼 토글
    btnEdit.classList.toggle("d-none", isEditMode);
    btnSave.classList.toggle("d-none", !isEditMode);
    btnDone.classList.toggle("d-none", !isEditMode);

    log("setEditUI", { isEditMode });
  }

  function enableSortable() {
    if (sortable) return;
    sortable = new Sortable(listEl, {
      animation: 150,
      handle: ".manual-drag-handle",
      draggable: "a.manual-item",
      ghostClass: "sortable-ghost",
    });
    log("sortable enabled");
  }

  function disableSortable() {
    if (!sortable) return;
    sortable.destroy();
    sortable = null;
    log("sortable disabled");
  }

  /* -----------------------------
   * actions
   * ----------------------------- */
  async function saveOrder() {
    const ordered_ids = getOrderedIds();

    if (ordered_ids.length === 0) {
      alertBox("저장할 항목이 없습니다.");
      return;
    }

    setBtnLoading(btnSave, true, "저장중...");
    try {
      await postJson(reorderUrl, { ordered_ids }, csrfToken);
      alertBox("순서가 저장되었습니다.");
    } catch (err) {
      console.error("[manual_list_edit] saveOrder error", err);
      alertBox(err?.message || "저장 중 오류가 발생했습니다.");
    } finally {
      setBtnLoading(btnSave, false);
    }
  }

  async function deleteManual(btn) {
    const item = btn?.closest?.("a.manual-item");
    const id = item?.dataset?.id;

    if (!item || !isDigits(id)) return;

    if (!confirm("정말 삭제하시겠습니까?")) return;

    setBtnLoading(btn, true, "삭제중...");
    try {
      await postJson(deleteUrl, { id: Number(id) }, csrfToken);
      item.remove();
    } catch (err) {
      console.error("[manual_list_edit] delete error", err);
      alertBox(err?.message || "삭제 중 오류가 발생했습니다.");
      setBtnLoading(btn, false);
    }
  }

  /* -----------------------------
   * events
   * ----------------------------- */
  // 편집 진입
  btnEdit.addEventListener("click", () => {
    setEditUI(true);
    enableSortable();
  });

  // 완료(편집 종료)
  btnDone.addEventListener("click", () => {
    disableSortable();
    setEditUI(false);
  });

  // 순서 저장
  btnSave.addEventListener("click", saveOrder);

  // 삭제 (이벤트 위임)
  listEl.addEventListener("click", (e) => {
    const btn = e.target?.closest?.(".btn-manual-delete");
    if (!btn) return;

    // 편집모드에서만 동작
    if (!isEditMode) return;

    e.preventDefault();
    e.stopPropagation();

    deleteManual(btn);
  });

  // 편집모드일 때 a 클릭 시 이동 방지 (이중 안전장치)
  listEl.addEventListener("click", (e) => {
    if (!isEditMode) return;
    const a = e.target?.closest?.("a.manual-item");
    if (!a) return;
    e.preventDefault();
  });

  // 초기 상태
  setEditUI(false);
})();
