// django_ma/static/js/manual/manual_list_edit.js
(() => {
  const boot = window.ManualListBoot || {};
  const listEl = document.getElementById("manualListGroup");
  const btnEdit = document.getElementById("btnManualEditMode");
  const btnSave = document.getElementById("btnManualSaveOrder");
  const btnDone = document.getElementById("btnManualDone");
  const csrfForm = document.getElementById("manualEditCsrfForm");

  if (!listEl || !btnEdit || !btnSave || !btnDone || !csrfForm) return;

  if (typeof window.Sortable === "undefined") {
    console.error("[manual_list_edit] SortableJS not loaded.");
    return;
  }

  const toStr = (v) => String(v ?? "").trim();
  const isDigits = (v) => /^\d+$/.test(String(v ?? ""));
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const reorderUrl = toStr(boot.reorderUrl);
  const deleteUrl = toStr(boot.deleteUrl);
  const updateTitleUrl = toStr(boot.updateTitleUrl);

  function getCSRFToken() {
    const el = csrfForm.querySelector('input[name="csrfmiddlewaretoken"]');
    return toStr(el?.value);
  }
  const csrfToken = getCSRFToken();

  function alertBox(msg) {
    window.alert(toStr(msg) || "오류가 발생했습니다.");
  }

  async function safeReadJson(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) return { __non_json__: true };
    return await res.json().catch(() => ({}));
  }

  async function postJson(url, bodyObj) {
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

  function getItems() {
    return qsa("a.manual-item", listEl);
  }

  function getOrderedIds() {
    return getItems().map((a) => a.dataset.id).filter(isDigits);
  }

  // Sortable instance
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

  function toggleTitleEditor(isEdit) {
    getItems().forEach((a) => {
      const textEl = a.querySelector(".manual-title-text");
      const inputEl = a.querySelector(".manual-title-input");
      if (!textEl || !inputEl) return;

      if (isEdit) {
        inputEl.value = toStr(textEl.textContent);
        textEl.classList.add("d-none");
        inputEl.classList.remove("d-none");
      } else {
        textEl.classList.remove("d-none");
        inputEl.classList.add("d-none");
      }
    });
  }

  function setEditUI(nextEdit) {
    isEditMode = !!nextEdit;

    // 핸들/삭제 버튼 토글
    qsa(".manual-drag-handle", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));
    qsa(".btn-manual-delete", listEl).forEach((el) => el.classList.toggle("d-none", !isEditMode));

    // 타이틀 인라인 수정 토글
    toggleTitleEditor(isEditMode);

    // 링크 이동 막기
    getItems().forEach((a) => {
      if (isEditMode) {
        if (!a.dataset.href) a.dataset.href = a.getAttribute("href") || "";
        a.setAttribute("href", "javascript:void(0)");
      } else {
        a.setAttribute("href", a.dataset.href || "#");
      }
      a.classList.toggle("manual-editing", isEditMode);
    });

    btnEdit.classList.toggle("d-none", isEditMode);
    btnSave.classList.toggle("d-none", !isEditMode);
    btnDone.classList.toggle("d-none", !isEditMode);
  }

  async function saveTitles() {
    if (!updateTitleUrl) return;

    const tasks = [];
    getItems().forEach((a) => {
      const id = a.dataset.id;
      if (!isDigits(id)) return;

      const inputEl = a.querySelector(".manual-title-input");
      const textEl = a.querySelector(".manual-title-text");
      if (!inputEl || !textEl) return;

      const newTitle = toStr(inputEl.value);
      const oldTitle = toStr(textEl.textContent);

      if (!newTitle) throw new Error("제목은 비워둘 수 없습니다.");
      if (newTitle.length > 80) throw new Error("제목은 80자 이하여야 합니다.");

      // 변경된 것만 서버 호출
      if (newTitle !== oldTitle) {
        tasks.push(
          postJson(updateTitleUrl, { id: Number(id), title: newTitle }).then((data) => {
            textEl.textContent = data?.title || newTitle;
          })
        );
      }
    });

    await Promise.all(tasks);
  }

  async function saveAll() {
    try {
      btnSave.disabled = true;
      btnSave.textContent = "저장중...";

      // 1) 제목 저장
      await saveTitles();

      // 2) 순서 저장
      const ordered_ids = getOrderedIds();
      await postJson(reorderUrl, { ordered_ids });

      btnSave.textContent = "순서 저장";
      alertBox("저장되었습니다.");
    } catch (e) {
      console.error(e);
      alertBox(e?.message || "저장 중 오류가 발생했습니다.");
      btnSave.textContent = "순서 저장";
    } finally {
      btnSave.disabled = false;
    }
  }

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

  // 저장(제목+순서)
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
      console.error(err);
      alertBox(err?.message || "삭제 중 오류가 발생했습니다.");
      btn.disabled = false;
    }
  });

  // 편집모드일 때 a 클릭 시 이동 방지
  listEl.addEventListener("click", (e) => {
    if (!isEditMode) return;
    const a = e.target?.closest?.("a.manual-item");
    if (!a) return;
    e.preventDefault();
  });

  // 초기 상태
  setEditUI(false);
})();
