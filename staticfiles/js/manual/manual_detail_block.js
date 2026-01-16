// django_ma/static/js/manual/manual_detail_block.js
// -----------------------------------------------------------------------------
// Manual Detail Blocks (FINAL - Refactor)
// - 섹션(카드): 추가/삭제/소제목 수정
// - 블록: 추가/수정/삭제/정렬(정렬은 별도 파일이면 그대로 유지 가능)
// - Quill: attach 업로드 후 링크 삽입
// - 이미지: preview + viewer
// - 기존 DOM id/class/dataset/응답키 유지
// -----------------------------------------------------------------------------

(() => {
  const S = window.ManualShared;
  if (!S) {
    console.error("[manual_detail_block] ManualShared not loaded. (_shared.js 포함 확인)");
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
   * 0) DOM refs / boot urls
   * ========================================================================= */
  const modalEl = document.getElementById("manualBlockModal");
  const sectionsEl = document.getElementById("manualSections");

  const btnSave = document.getElementById("btnManualBlockSave");
  const titleEl = document.getElementById("manualBlockModalTitle");
  const errBox = document.getElementById("manualBlockError");
  const csrfForm = document.getElementById("manualBlockCsrfForm");

  const btnAddSection = document.getElementById("btnAddManualSection");
  const btnGoTop = document.getElementById("btnManualGoTop");

  // image inputs
  const imgInput = document.getElementById("manualBlockImageInput");
  const imgPreviewWrap = document.getElementById("manualBlockImagePreviewWrap");
  const imgPreview = document.getElementById("manualBlockImagePreview");
  const removeWrap = document.getElementById("manualBlockRemoveImageWrap");
  const removeChk = document.getElementById("manualBlockRemoveImage");

  // viewer modal
  const viewerModalEl = document.getElementById("manualImageViewer");
  const viewerImg = document.getElementById("manualViewerImg");

  // quill attachment input
  const attachInput = document.getElementById("manualQuillAttachInput");

  const bootEl = document.getElementById("manualDetailBoot");
  const sectionTitleUpdateUrl = toStr(bootEl?.dataset?.sectionTitleUpdateUrl || "");
  const sectionDeleteUrl = toStr(bootEl?.dataset?.sectionDeleteUrl || "");
  const blockDeleteUrl = toStr(bootEl?.dataset?.blockDeleteUrl || "");

  if (!modalEl || !sectionsEl || !btnSave || !titleEl || !errBox || !csrfForm) return;

  // 중복 바인딩 방지(기존 유지)
  if (document.documentElement.dataset.manualDetailBound === "true") return;
  document.documentElement.dataset.manualDetailBound = "true";

  const csrfToken = getCSRFTokenFromForm(csrfForm);

  // TOP
  btnGoTop?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  const api = {
    json: (url, body) => postJson(url, body, csrfToken),
    form: (url, fd) => postForm(url, fd, csrfToken),
  };

  function err(msg) {
    showErrorBox(errBox, msg, false);
  }

  /* =========================================================================
   * 1) State
   * ========================================================================= */
  let mode = "add";          // add | edit
  let editingBlockId = null; // number|null
  let currentSectionId = null;

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

  /* =========================================================================
   * 3) Viewer
   * ========================================================================= */
  function openViewer(url) {
    if (!viewerModalEl || !viewerImg) return;
    viewerImg.src = url;
    const m = new bootstrap.Modal(viewerModalEl);
    m.show();
  }

  /* =========================================================================
   * 4) Quill + Attachments
   * ========================================================================= */
  let quill = null;

  function ensureQuill() {
    if (quill) return quill;
    if (typeof window.Quill === "undefined") throw new Error("Quill이 로드되지 않았습니다.");

    quill = new Quill("#manualQuillEditor", {
      theme: "snow",
      modules: {
        toolbar: {
          container: [
            [{ header: [1, 2, 3, false] }],
            ["bold", "italic", "underline", "strike"],
            [{ color: [] }, { background: [] }],
            [{ align: [] }, { indent: "-1" }, { indent: "+1" }],
            [{ list: "ordered" }, { list: "bullet" }],
            ["link", "attach"], // ✅ attach 버튼
            ["clean"],
          ],
          handlers: {
            attach: () => {
              clearErrorBox(errBox);
              if (!attachInput) return err("첨부 입력 요소가 없습니다. (#manualQuillAttachInput)");
              if (mode !== "edit" || !editingBlockId) {
                return err("첨부는 '먼저 저장된 블록'에서만 가능합니다. 저장 후 '수정'에서 첨부해주세요.");
              }
              attachInput.value = "";
              attachInput.click();
            },
          },
        },
      },
    });

    // attach 버튼 아이콘/타이틀 부여(기존 유지)
    setTimeout(() => {
      const btn = document.querySelector(".ql-attach");
      if (btn) {
        btn.type = "button";
        btn.title = "첨부파일 업로드";
        btn.innerHTML = "📎";
      }
    }, 0);

    return quill;
  }

  // 모달 뜰 때 Quill 업데이트
  modalEl.addEventListener("shown.bs.modal", () => {
    try {
      ensureQuill().update("silent");
    } catch (e) {
      err(e?.message);
    }
  });

  function insertAttachmentLink(att) {
    const url = toStr(att?.url);
    const name = toStr(att?.name) || "첨부파일";
    const sizeText = att?.size ? ` (${formatBytes(att.size)})` : "";

    if (!url) throw new Error("첨부 URL이 없습니다.");

    const q = ensureQuill();
    const sel = q.getSelection(true);
    const index = sel ? sel.index : q.getLength();

    q.insertText(index, name + sizeText, { link: url });
    q.insertText(index + (name + sizeText).length, "\n");
    q.setSelection(index + (name + sizeText).length + 1, 0, "silent");
  }

  async function uploadAttachmentFile(file) {
    const uploadUrl = toStr(modalEl.dataset.attachUploadUrl);
    if (!uploadUrl) throw new Error("첨부 업로드 URL이 없습니다. (data-attach-upload-url)");
    if (!editingBlockId || mode !== "edit") {
      throw new Error("첨부는 '저장된 블록'에서만 가능합니다. 먼저 블록을 저장한 뒤, 수정에서 첨부해주세요.");
    }

    const fd = new FormData();
    fd.append("block_id", String(editingBlockId));
    fd.append("file", file);

    const data = await api.form(uploadUrl, fd);
    return data?.attachment;
  }

  attachInput?.addEventListener("change", async () => {
    clearErrorBox(errBox);
    const f = attachInput.files?.[0];
    if (!f) return;

    try {
      const att = await uploadAttachmentFile(f);
      insertAttachmentLink(att);
    } catch (e) {
      console.error(e);
      err(e?.message || "첨부 업로드 중 오류가 발생했습니다.");
    } finally {
      attachInput.value = "";
    }
  });

  /* =========================================================================
   * 5) Open modal: add/edit
   * ========================================================================= */
  function openForAdd(sectionId) {
    mode = "add";
    editingBlockId = null;
    currentSectionId = sectionId || null;

    titleEl.textContent = "내용 추가";
    clearErrorBox(errBox);
    resetImageUI();

    setTimeout(() => {
      try { ensureQuill().setContents([]); } catch (_) {}
    }, 0);
  }

  function openForEdit(blockEl) {
    const bid = blockEl?.dataset?.blockId;
    if (!isDigits(bid)) return;

    mode = "edit";
    editingBlockId = Number(bid);
    currentSectionId = null;

    titleEl.textContent = "내용 수정";
    clearErrorBox(errBox);
    resetImageUI();

    const imgUrl = toStr(blockEl.dataset.imageUrl);
    if (imgUrl) {
      showPreviewFromUrl(imgUrl);
      removeWrap?.classList.remove("d-none");
    }

    const html = blockEl.querySelector(".manual-block-content")?.innerHTML || "";
    setTimeout(() => {
      try { ensureQuill().clipboard.dangerouslyPasteHTML(html); } catch (_) {}
    }, 0);
  }

  /* =========================================================================
   * 6) Builders (DOM 생성)
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
    const sec = document.createElement("div");
    sec.className = "card p-4 mb-3 manual-section";
    sec.dataset.sectionId = sectionId;

    const safeTitle = toStr(titleText);
    const titleHtml = safeTitle ? safeTitle : "(소제목 없음)";
    const titleClass = safeTitle ? "" : "empty";

    sec.innerHTML = `
      <div class="sec-card-actions">
        <button type="button"
                class="btn btn-sm btn-danger btnDeleteSection"
                data-section-id="${sectionId}">카드 삭제</button>
      </div>

      <div class="sec-title-row">
        <h5 class="sec-title ${titleClass}" data-role="secTitleText">${titleHtml}</h5>
        <div class="sec-title-actions">
          <button type="button" class="btn btn-sm btn-outline-secondary btnEditSectionTitle">소제목 수정</button>
        </div>
      </div>

      <div class="manualBlocks" id="manualBlocks-${sectionId}"></div>

      <div class="d-flex justify-content-end mt-2">
        <button type="button"
                class="btn btn-sm btn-primary btn-add-block"
                data-bs-toggle="modal"
                data-bs-target="#manualBlockModal"
                data-section-id="${sectionId}">+내용추가</button>
      </div>
    `;
    return sec;
  }

  /* =========================================================================
   * 7) Section title inline edit
   * ========================================================================= */
  function beginSectionTitleEdit(sectionEl) {
    const sid = sectionEl?.dataset?.sectionId;
    if (!isDigits(sid)) return;

    if (!sectionTitleUpdateUrl) {
      alert("섹션 소제목 업데이트 URL이 없습니다. (manualDetailBoot 확인)");
      return;
    }

    // 중복 에디팅 방지
    if (sectionEl.dataset.titleEditing === "1") return;
    sectionEl.dataset.titleEditing = "1";

    const titleTextEl = sectionEl.querySelector('[data-role="secTitleText"]');
    if (!titleTextEl) return;

    const editBtn = sectionEl.querySelector(".btnEditSectionTitle");
    const prevEditBtnDisplay = editBtn?.style?.display ?? "";
    if (editBtn) editBtn.style.display = "none";

    const currentTextRaw = toStr(titleTextEl.textContent);
    const currentValue = currentTextRaw === "(소제목 없음)" ? "" : currentTextRaw;

    const wrap = document.createElement("div");
    wrap.className = "sec-title-edit-wrap";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-control form-control-sm sec-title-edit";
    input.maxLength = 120;
    input.placeholder = "소제목 입력 (최대 120자)";
    input.value = currentValue;

    const btns = document.createElement("div");
    btns.className = "sec-title-btns";

    const btnOk = document.createElement("button");
    btnOk.type = "button";
    btnOk.className = "btn btn-sm btn-primary";
    btnOk.textContent = "저장";

    const btnCancel = document.createElement("button");
    btnCancel.type = "button";
    btnCancel.className = "btn btn-sm btn-outline-secondary";
    btnCancel.textContent = "취소";

    btns.appendChild(btnOk);
    btns.appendChild(btnCancel);

    wrap.appendChild(input);
    wrap.appendChild(btns);

    titleTextEl.style.display = "none";
    titleTextEl.insertAdjacentElement("afterend", wrap);

    const cleanup = () => {
      wrap.remove();
      titleTextEl.style.display = "";
      sectionEl.dataset.titleEditing = "0";
      if (editBtn) editBtn.style.display = prevEditBtnDisplay;
    };

    const applyNewTitle = (newValue) => {
      const v = toStr(newValue);
      if (v) {
        titleTextEl.textContent = v;
        titleTextEl.classList.remove("empty");
      } else {
        titleTextEl.textContent = "(소제목 없음)";
        titleTextEl.classList.add("empty");
      }
    };

    const save = async () => {
      const newValue = toStr(input.value);

      btnOk.disabled = true;
      btnCancel.disabled = true;
      input.disabled = true;

      try {
        const data = await api.json(sectionTitleUpdateUrl, {
          section_id: Number(sid),
          title: newValue,
        });
        applyNewTitle(data?.section?.title ?? newValue);
        cleanup();
      } catch (e) {
        console.error(e);
        alert(e?.message || "소제목 저장 중 오류가 발생했습니다.");
        btnOk.disabled = false;
        btnCancel.disabled = false;
        input.disabled = false;
        input.focus();
      }
    };

    btnOk.addEventListener("click", save);
    btnCancel.addEventListener("click", cleanup);

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); save(); }
      if (e.key === "Escape") { e.preventDefault(); cleanup(); }
    });

    setTimeout(() => { input.focus(); input.select(); }, 0);
  }

  /* =========================================================================
   * 8) Delete helpers
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

  async function deleteSectionById(sectionId, sectionEl) {
    if (!sectionDeleteUrl) return alert("섹션 삭제 URL이 없습니다. (manualDetailBoot 확인)");
    if (!isDigits(sectionId)) return alert("section_id가 올바르지 않습니다.");
    if (!confirm("이 카드를 삭제할까요?\n(카드 안의 내용도 함께 삭제됩니다.)")) return;

    try {
      const data = await api.json(sectionDeleteUrl, { section_id: Number(sectionId) });
      sectionEl?.remove();

      // 마지막 섹션 삭제 시 서버가 기본 섹션 생성해서 new_section 반환 (기존 동작 유지)
      if (data?.new_section?.id && isDigits(data.new_section.id)) {
        const newSec = buildSectionElement(Number(data.new_section.id), data.new_section.title || "");
        sectionsEl.appendChild(newSec);
        newSec.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    } catch (e) {
      console.error(e);
      alert(e?.message || "카드 삭제 중 오류가 발생했습니다.");
    }
  }

  /* =========================================================================
   * 9) Events (delegation)
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
      if (sectionEl) beginSectionTitleEdit(sectionEl);
      return;
    }

    // 섹션 삭제
    const delSectionBtn = t?.closest?.(".btnDeleteSection");
    if (delSectionBtn) {
      const sectionId =
        delSectionBtn.getAttribute("data-section-id") ||
        delSectionBtn.closest(".manual-section")?.dataset?.sectionId;
      const sectionEl = delSectionBtn.closest(".manual-section");
      deleteSectionById(sectionId, sectionEl);
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

  /* =========================================================================
   * 10) +구역추가
   * ========================================================================= */
  btnAddSection?.addEventListener("click", async () => {
    const manualId = toStr(btnAddSection.dataset.manualId);
    const url = toStr(btnAddSection.dataset.sectionAddUrl);

    if (!isDigits(manualId)) return alert("manual_id가 올바르지 않습니다.");
    if (!url) return alert("section_add_url이 없습니다. (data-section-add-url 확인)");

    btnAddSection.disabled = true;
    const oldText = btnAddSection.textContent;
    btnAddSection.textContent = "추가중...";

    try {
      const data = await api.json(url, { manual_id: Number(manualId) });
      const sid = data?.section?.id;
      if (!isDigits(sid)) throw new Error("section id가 응답에 없습니다.");

      const newSectionEl = buildSectionElement(Number(sid), "");
      sectionsEl.appendChild(newSectionEl);
      newSectionEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      console.error(err);
      alert(err?.message || "구역 추가 중 오류가 발생했습니다.");
    } finally {
      btnAddSection.disabled = false;
      btnAddSection.textContent = oldText;
    }
  });

  /* =========================================================================
   * 11) Save (add/edit) - FormData
   * ========================================================================= */
  btnSave.addEventListener("click", async () => {
    clearErrorBox(errBox);

    const addUrl = toStr(modalEl.dataset.addUrl);
    const updateUrl = toStr(modalEl.dataset.updateUrl);
    const manualId = toStr(modalEl.dataset.manualId);

    let html = "";
    try {
      html = toStr(ensureQuill().root.innerHTML);
    } catch (e) {
      return err(e?.message || "편집기 초기화에 실패했습니다.");
    }

    // 빈 내용 방지(기존 로직 유지)
    const normalized = html.replace(/\s+/g, "").toLowerCase();
    if (!html || normalized === "<p><br></p>" || normalized === "<p></p>") {
      return err("텍스트 내용을 입력해주세요.");
    }

    btnSave.disabled = true;
    const oldText = btnSave.textContent;
    btnSave.textContent = "저장중...";

    try {
      const fd = new FormData();

      if (mode === "add") {
        if (!isDigits(manualId)) throw new Error("manual_id가 올바르지 않습니다.");
        if (!isDigits(currentSectionId)) throw new Error("추가할 구역(section)이 지정되지 않았습니다.");

        fd.append("manual_id", String(manualId));
        fd.append("section_id", String(currentSectionId));
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
        if (!editingBlockId) throw new Error("수정 대상이 없습니다.");

        fd.append("block_id", String(editingBlockId));
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
      err(errObj?.message || "저장 중 오류가 발생했습니다.");
    } finally {
      btnSave.disabled = false;
      btnSave.textContent = oldText;
    }
  });

  /* =========================================================================
   * 12) modal reset
   * ========================================================================= */
  modalEl.addEventListener("hidden.bs.modal", () => {
    mode = "add";
    editingBlockId = null;
    currentSectionId = null;
    clearErrorBox(errBox);
    resetImageUI();
    try { ensureQuill().setContents([]); } catch (_) {}
    if (attachInput) attachInput.value = "";
  });
})();
