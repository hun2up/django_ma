// django_ma/static/js/manual/manual_detail_block/index.js
// -----------------------------------------------------------------------------
// Manual Detail Blocks (Minimal split - Entry)
// - 이벤트 위임 + 상태/오케스트레이션
// - Quill/첨부: ./quill.js
// - 섹션 CRUD + Subnav 반영: ./section_subnav.js
// -----------------------------------------------------------------------------

import { createQuillManager } from "./quill.js";
import { createSectionSubnavManager } from "./section_subnav.js";

(() => {
  const S = window.ManualShared;
  if (!S) {
    console.error("[manual_detail_block/index] ManualShared not loaded.");
    return;
  }

  const {
    toStr,
    isDigits,
    getCSRFTokenFromForm,
    showErrorBox,
    clearErrorBox,
    postJson,
    postForm,
    formatBytes,
  } = S;

  /* =========================================================================
   * 0) DOM refs
   * ========================================================================= */
  const modalEl = document.getElementById("manualBlockModal");
  const sectionsEl = document.getElementById("manualSections");

  const btnSave = document.getElementById("btnManualBlockSave");
  const titleEl = document.getElementById("manualBlockModalTitle");
  const errBox = document.getElementById("manualBlockError");
  const csrfForm = document.getElementById("manualBlockCsrfForm");

  const btnAddSection = document.getElementById("btnAddManualSection");
  const btnGoTop = document.getElementById("btnManualGoTop");

  const imgInput = document.getElementById("manualBlockImageInput");
  const imgPreviewWrap = document.getElementById("manualBlockImagePreviewWrap");
  const imgPreview = document.getElementById("manualBlockImagePreview");
  const removeWrap = document.getElementById("manualBlockRemoveImageWrap");
  const removeChk = document.getElementById("manualBlockRemoveImage");

  const viewerModalEl = document.getElementById("manualImageViewer");
  const viewerImg = document.getElementById("manualViewerImg");

  const attachInput = document.getElementById("manualQuillAttachInput");

  const bootEl = document.getElementById("manualDetailBoot");
  const sectionTitleUpdateUrl = toStr(bootEl?.dataset?.sectionTitleUpdateUrl || "");
  const sectionDeleteUrl = toStr(bootEl?.dataset?.sectionDeleteUrl || "");
  const blockDeleteUrl = toStr(bootEl?.dataset?.blockDeleteUrl || "");

  if (!modalEl || !sectionsEl || !btnSave || !titleEl || !errBox || !csrfForm) return;

  /* =========================================================================
   * 0.1) Bind guard
   * ========================================================================= */
  if (document.documentElement.dataset.manualDetailBound === "true") return;
  document.documentElement.dataset.manualDetailBound = "true";

  const csrfToken = getCSRFTokenFromForm(csrfForm);

  const api = {
    json: (url, body) => postJson(url, body, csrfToken),
    form: (url, fd) => postForm(url, fd, csrfToken),
  };

  const ui = {
    err: (msg) => showErrorBox(errBox, msg, false),
    clearErr: () => clearErrorBox(errBox),
  };

  /* =========================================================================
   * 1) State
   * ========================================================================= */
  const state = {
    mode: "add",              // add | edit
    editingBlockId: null,     // number|null
    currentSectionId: null,   // number|null
  };

  /* =========================================================================
   * 2) Image UI
   * ========================================================================= */
  function resetImageUI() {
    if (imgInput) imgInput.value = "";
    if (imgPreviewWrap) imgPreviewWrap.style.display = "none";
    if (imgPreview) imgPreview.src = "";
    if (removeWrap) removeWrap.classList.add("d-none");
    if (removeChk) removeChk.checked = false;
  }

  function showPreviewFromUrl(url) {
    if (!imgPreviewWrap || !imgPreview) return;
    if (!url) {
      imgPreviewWrap.style.display = "none";
      imgPreview.src = "";
      return;
    }
    imgPreview.src = url;
    imgPreviewWrap.style.display = "";
  }

  imgInput?.addEventListener("change", () => {
    const file = imgInput?.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    showPreviewFromUrl(url);
  });

  function openViewer(url) {
    if (!viewerModalEl || !viewerImg) return;
    viewerImg.src = url;
    const m = new bootstrap.Modal(viewerModalEl);
    m.show();
  }

  /* =========================================================================
   * 3) Quill manager (attach 포함)
   * ========================================================================= */
  const quillMgr = createQuillManager({
    S,
    modalEl,
    errBox,
    attachInput,
    api,
    state,
    formatBytes,
  });

  modalEl.addEventListener("shown.bs.modal", () => quillMgr.onModalShown());

  /* =========================================================================
   * 4) Section + Subnav manager
   * ========================================================================= */
  const secMgr = createSectionSubnavManager({
    S,
    api,
    sectionsEl,
    btnAddSection,
    sectionTitleUpdateUrl,
    sectionDeleteUrl,
  });

  /* =========================================================================
   * 5) Builders
   * ========================================================================= */
  function buildBlockElement(b) {
    const wrapper = document.createElement("div");
    wrapper.className = "border rounded-3 p-3 mb-3 manual-block";
    wrapper.dataset.blockId = b.id;
    wrapper.dataset.imageUrl = b.image_url || "";

    const leftHtml = b.image_url
      ? `<img src="${b.image_url}" class="manual-block-thumb jsManualImg" alt="manual image">`
      : `<div class="text-muted small py-4">이미지 없음</div>`;

    wrapper.innerHTML = `
      <div class="manual-block-grid">
        <div class="manual-block-media">${leftHtml}</div>
        <div class="manual-block-text manual-block-content">${b.content || ""}</div>
      </div>

      <div class="manual-block-actions">
        <button type="button"
                class="btn btn-sm btn-outline-secondary btn-edit-block"
                data-bs-toggle="modal"
                data-bs-target="#manualBlockModal">수정</button>
        <button type="button"
                class="btn btn-sm btn-outline-danger btn-delete-block"
                data-block-id="${b.id}">삭제</button>
      </div>
    `;
    return wrapper;
  }

  function buildSectionElement(sectionId, titleText = "") {
    // section_subnav.js 쪽에서도 사용해야 해서 secMgr로 위임
    return secMgr.buildSectionElement(sectionId, titleText);
  }

  /* =========================================================================
   * 6) Modal open helpers
   * ========================================================================= */
  function openForAdd(sectionId) {
    state.mode = "add";
    state.editingBlockId = null;
    state.currentSectionId = sectionId || null;

    titleEl.textContent = "내용 추가";
    ui.clearErr();
    resetImageUI();

    setTimeout(() => quillMgr.setHtml(""), 0);
  }

  function openForEdit(blockEl) {
    const bid = blockEl?.dataset?.blockId;
    if (!isDigits(bid)) return;

    state.mode = "edit";
    state.editingBlockId = Number(bid);
    state.currentSectionId = null;

    titleEl.textContent = "내용 수정";
    ui.clearErr();
    resetImageUI();

    const imgUrl = toStr(blockEl.dataset.imageUrl);
    if (imgUrl) {
      showPreviewFromUrl(imgUrl);
      removeWrap?.classList.remove("d-none");
    }

    const html = blockEl.querySelector(".manual-block-content")?.innerHTML || "";
    setTimeout(() => quillMgr.setHtml(html), 0);
  }

  /* =========================================================================
   * 7) Delete helpers
   * ========================================================================= */
  async function deleteBlockById(blockId, blockEl) {
    if (!blockDeleteUrl) return alert("블록 삭제 URL이 없습니다. (manualDetailBoot 확인)");
    if (!isDigits(blockId)) return alert("block_id가 올바르지 않습니다.");
    if (!confirm("이 블록을 삭제할까요?")) return;

    try {
      await api.json(blockDeleteUrl, { block_id: Number(blockId) });
      blockEl?.remove();
    } catch (e) {
      console.error(e);
      alert(e?.message || "블록 삭제 중 오류가 발생했습니다.");
    }
  }

  /* =========================================================================
   * 8) Events (delegation)
   * ========================================================================= */
  sectionsEl.addEventListener("click", (e) => {
    const t = e.target;

    // 이미지 클릭 -> viewer
    const imgEl = t?.closest?.(".jsManualImg");
    if (imgEl) {
      const blockEl = imgEl.closest(".manual-block");
      const url = toStr(blockEl?.dataset?.imageUrl) || toStr(imgEl.getAttribute("src"));
      if (url) openViewer(url);
      return;
    }

    // 섹션 소제목 수정
    const editTitleBtn = t?.closest?.(".btnEditSectionTitle");
    if (editTitleBtn) {
      const sectionEl = editTitleBtn.closest(".manual-section");
      if (sectionEl) secMgr.beginSectionTitleEdit(sectionEl);
      return;
    }

    // 섹션 삭제
    const delSectionBtn = t?.closest?.(".btnDeleteSection");
    if (delSectionBtn) {
      const sectionId =
        delSectionBtn.getAttribute("data-section-id") ||
        delSectionBtn.closest(".manual-section")?.dataset?.sectionId;
      const sectionEl = delSectionBtn.closest(".manual-section");
      secMgr.deleteSectionById(sectionId, sectionEl);
      return;
    }

    // 블록 추가 모달 open
    const addBtn = t?.closest?.(".btn-add-block");
    if (addBtn) {
      const sid = addBtn.getAttribute("data-section-id");
      if (isDigits(sid)) openForAdd(Number(sid));
      return;
    }

    // 블록 수정 모달 open
    const editBtn = t?.closest?.(".btn-edit-block");
    if (editBtn) {
      const blockEl = editBtn.closest(".manual-block");
      if (blockEl) openForEdit(blockEl);
      return;
    }

    // 블록 삭제
    const delBlockBtn = t?.closest?.(".btn-delete-block");
    if (delBlockBtn) {
      const blockId =
        delBlockBtn.getAttribute("data-block-id") ||
        delBlockBtn.closest(".manual-block")?.dataset?.blockId;
      const blockEl = delBlockBtn.closest(".manual-block");
      deleteBlockById(blockId, blockEl);
      return;
    }
  });

  // TOP
  btnGoTop?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  /* =========================================================================
   * 9) Save (add/edit) - FormData
   * ========================================================================= */
  btnSave.addEventListener("click", async () => {
    ui.clearErr();

    const addUrl = toStr(modalEl.dataset.addUrl);
    const updateUrl = toStr(modalEl.dataset.updateUrl);
    const manualId = toStr(modalEl.dataset.manualId);

    let html = "";
    try {
      html = toStr(quillMgr.getHtml());
    } catch (e) {
      return ui.err(e?.message || "편집기 초기화에 실패했습니다.");
    }

    const normalized = html.replace(/\s+/g, "").toLowerCase();
    if (!html || normalized === "<p><br></p>" || normalized === "<p></p>") {
      return ui.err("텍스트 내용을 입력해주세요.");
    }

    btnSave.disabled = true;
    const oldText = btnSave.textContent;
    btnSave.textContent = "저장중...";

    try {
      const fd = new FormData();

      if (state.mode === "add") {
        if (!isDigits(manualId)) throw new Error("manual_id가 올바르지 않습니다.");
        if (!isDigits(state.currentSectionId)) throw new Error("추가할 구역(section)이 지정되지 않았습니다.");

        fd.append("manual_id", String(manualId));
        fd.append("section_id", String(state.currentSectionId));
        fd.append("content", html);
        if (imgInput?.files?.[0]) fd.append("image", imgInput.files[0]);

        const data = await api.form(addUrl, fd);
        const b = data.block;
        const sid = toStr(b?.section_id);

        const container = document.getElementById(`manualBlocks-${sid}`);
        if (!container) throw new Error(`manualBlocks-${sid} 컨테이너를 찾을 수 없습니다.`);

        const newEl = buildBlockElement(b);
        container.appendChild(newEl);
        newEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        if (!state.editingBlockId) throw new Error("수정 대상이 없습니다.");

        fd.append("block_id", String(state.editingBlockId));
        fd.append("content", html);
        if (removeChk?.checked) fd.append("remove_image", "1");
        if (imgInput?.files?.[0]) fd.append("image", imgInput.files[0]);

        const data = await api.form(updateUrl, fd);
        const b = data.block;

        const target = sectionsEl.querySelector(`.manual-block[data-block-id="${b.id}"]`);
        if (target) {
          target.dataset.imageUrl = b.image_url || "";

          const contentEl = target.querySelector(".manual-block-content");
          if (contentEl) contentEl.innerHTML = b.content || "";

          const media = target.querySelector(".manual-block-media");
          if (media) {
            media.innerHTML = b.image_url
              ? `<img src="${b.image_url}" class="manual-block-thumb jsManualImg" alt="manual image">`
              : `<div class="text-muted small py-4">이미지 없음</div>`;
          }
        }
      }

      bootstrap.Modal.getInstance(modalEl)?.hide();
    } catch (errObj) {
      console.error(errObj);
      ui.err(errObj?.message || "저장 중 오류가 발생했습니다.");
    } finally {
      btnSave.disabled = false;
      btnSave.textContent = oldText;
    }
  });

  /* =========================================================================
   * 10) modal reset
   * ========================================================================= */
  modalEl.addEventListener("hidden.bs.modal", () => {
    state.mode = "add";
    state.editingBlockId = null;
    state.currentSectionId = null;

    ui.clearErr();
    resetImageUI();
    quillMgr.reset();
    if (attachInput) attachInput.value = "";
  });

  /* =========================================================================
   * 11) Section add (버튼은 secMgr가 책임)
   * ========================================================================= */
  secMgr.bindAddSectionButton({
    buildSectionElement,
  });
})();
