(() => {
  /* =========================================================
   * 0) DOM refs
   * ========================================================= */
  const modalEl = document.getElementById("manualBlockModal");
  const sectionsEl = document.getElementById("manualSections");

  const btnSave = document.getElementById("btnManualBlockSave");
  const titleEl = document.getElementById("manualBlockModalTitle");
  const errBox = document.getElementById("manualBlockError");
  const csrfForm = document.getElementById("manualBlockCsrfForm");

  const btnAddSection = document.getElementById("btnAddManualSection");
  const btnGoTop = document.getElementById("btnManualGoTop");

  // ✅ image inputs
  const imgInput = document.getElementById("manualBlockImageInput");
  const imgPreviewWrap = document.getElementById("manualBlockImagePreviewWrap");
  const imgPreview = document.getElementById("manualBlockImagePreview");
  const removeWrap = document.getElementById("manualBlockRemoveImageWrap");
  const removeChk = document.getElementById("manualBlockRemoveImage");

  // ✅ viewer modal
  const viewerModalEl = document.getElementById("manualImageViewer");
  const viewerImg = document.getElementById("manualViewerImg");

  // ✅ quill attachment input
  const attachInput = document.getElementById("manualQuillAttachInput");

  const bootEl = document.getElementById("manualDetailBoot");
  const sectionTitleUpdateUrl = bootEl?.dataset?.sectionTitleUpdateUrl || "";
  const sectionDeleteUrl = bootEl?.dataset?.sectionDeleteUrl || "";
  const blockDeleteUrl = bootEl?.dataset?.blockDeleteUrl || "";

  // TOP
  btnGoTop?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  if (!modalEl || !sectionsEl || !btnSave || !titleEl || !errBox || !csrfForm) return;
  if (document.documentElement.dataset.manualDetailBound === "true") return;
  document.documentElement.dataset.manualDetailBound = "true";

  /* =========================================================
   * 1) utils
   * ========================================================= */
  const toStr = (v) => String(v ?? "").trim();
  const isDigits = (v) => /^\d+$/.test(String(v ?? ""));

  function getCSRFToken() {
    const el = csrfForm.querySelector('input[name="csrfmiddlewaretoken"]');
    return toStr(el?.value);
  }

  function showError(msg) {
    errBox.textContent = toStr(msg) || "오류가 발생했습니다.";
    errBox.classList.remove("d-none");
  }
  function clearError() {
    errBox.textContent = "";
    errBox.classList.add("d-none");
  }

  async function safeReadJson(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) return { __non_json__: true };
    return await res.json().catch(() => ({}));
  }

  // ✅ JSON 전송 (삭제/타이틀수정 등)
  async function postJson(url, bodyObj) {
    const csrf = getCSRFToken();
    if (!csrf) throw new Error("CSRF 토큰이 없습니다. (#manualBlockCsrfForm 확인)");
    if (!url) throw new Error("요청 URL이 비어있습니다.");

    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(bodyObj || {}),
    });

    const data = await safeReadJson(res);
    if (data?.__non_json__) throw new Error(`요청 실패 (HTTP ${res.status})`);
    if (!res.ok || !data?.ok) throw new Error(data?.message || `요청 실패 (HTTP ${res.status})`);
    return data;
  }

  // ✅ FormData 전송(이미지/파일 포함)
  async function postForm(url, formData) {
    const csrf = getCSRFToken();
    if (!csrf) throw new Error("CSRF 토큰이 없습니다. (#manualBlockCsrfForm 확인)");
    if (!url) throw new Error("요청 URL이 비어있습니다.");

    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: formData,
    });

    const data = await safeReadJson(res);
    if (data?.__non_json__) throw new Error(`요청 실패 (HTTP ${res.status})`);
    if (!res.ok || !data?.ok) throw new Error(data?.message || `요청 실패 (HTTP ${res.status})`);
    return data;
  }

  function formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!n) return "";
    const units = ["B", "KB", "MB", "GB"];
    let x = n;
    let idx = 0;
    while (x >= 1024 && idx < units.length - 1) {
      x /= 1024;
      idx += 1;
    }
    const v = idx === 0 ? String(Math.round(x)) : String(Math.round(x * 10) / 10);
    return `${v}${units[idx]}`;
  }

  /* =========================================================
   * 2) section title inline edit
   * ========================================================= */
  function beginSectionTitleEdit(sectionEl) {
    const sid = sectionEl?.dataset?.sectionId;
    if (!isDigits(sid)) return;

    if (!sectionTitleUpdateUrl) {
      alert("섹션 소제목 업데이트 URL이 없습니다. (manualDetailBoot 확인)");
      return;
    }

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
        const data = await postJson(sectionTitleUpdateUrl, {
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

  /* =========================================================
   * 3) Quill (toolbar: color + attach)
   * ========================================================= */
  let quill = null;

  function insertAttachmentLink(att) {
    const url = toStr(att?.url);
    const name = toStr(att?.name) || "첨부파일";
    const size = att?.size ? ` (${formatBytes(att.size)})` : "";

    if (!url) throw new Error("첨부 URL이 없습니다.");

    const q = ensureQuill();
    const sel = q.getSelection(true);
    const index = sel ? sel.index : q.getLength();

    // 파일 링크 + 줄바꿈(가독성)
    q.insertText(index, name + size, { link: url });
    q.insertText(index + (name + size).length, "\n");
    q.setSelection(index + (name + size).length + 1, 0, "silent");
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

    const data = await postForm(uploadUrl, fd);
    return data?.attachment;
  }

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
            ["link", "attach"],     // ✅ attach 버튼 추가
            ["clean"],
          ],
          handlers: {
            attach: () => {
              clearError();
              if (!attachInput) return showError("첨부 입력 요소가 없습니다. (#manualQuillAttachInput)");
              if (mode !== "edit" || !editingBlockId) {
                return showError("첨부는 '먼저 저장된 블록'에서만 가능합니다. 저장 후 '수정'에서 첨부해주세요.");
              }
              attachInput.value = "";
              attachInput.click();
            },
          },
        },
      },
    });

    // Quill이 만든 attach 버튼에 아이콘/타이틀 부여
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

  modalEl.addEventListener("shown.bs.modal", () => {
    try { ensureQuill().update("silent"); } catch (e) { showError(e?.message); }
  });

  // 첨부 파일 선택 → 업로드 → 링크 삽입
  attachInput?.addEventListener("change", async () => {
    clearError();
    const f = attachInput.files?.[0];
    if (!f) return;

    try {
      const att = await uploadAttachmentFile(f);
      insertAttachmentLink(att);
    } catch (e) {
      console.error(e);
      showError(e?.message || "첨부 업로드 중 오류가 발생했습니다.");
    } finally {
      attachInput.value = "";
    }
  });

  /* =========================================================
   * 4) state + image UI
   * ========================================================= */
  let mode = "add"; // add | edit
  let editingBlockId = null;
  let currentSectionId = null;

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
    if (!imgInput.files || !imgInput.files[0]) return;
    const file = imgInput.files[0];
    const url = URL.createObjectURL(file);
    showPreviewFromUrl(url);
  });

  function openForAdd(sectionId) {
    mode = "add";
    editingBlockId = null;
    currentSectionId = sectionId || null;

    titleEl.textContent = "내용 추가";
    clearError();
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
    clearError();
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

  /* =========================================================
   * 5) builders
   * ========================================================= */
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

  /* =========================================================
   * 6) delete helpers (JSON)
   * ========================================================= */
  async function deleteBlockById(blockId, blockEl) {
    if (!blockDeleteUrl) return alert("블록 삭제 URL이 없습니다. (manualDetailBoot 확인)");
    if (!isDigits(blockId)) return alert("block_id가 올바르지 않습니다.");
    if (!confirm("이 블록을 삭제할까요?")) return;

    try {
      await postJson(blockDeleteUrl, { block_id: Number(blockId) });
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
      const data = await postJson(sectionDeleteUrl, { section_id: Number(sectionId) });
      sectionEl?.remove();

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

  /* =========================================================
   * 7) image viewer
   * ========================================================= */
  function openViewer(url) {
    if (!viewerModalEl || !viewerImg) return;
    viewerImg.src = url;
    const modal = new bootstrap.Modal(viewerModalEl);
    modal.show();
  }

  /* =========================================================
   * 8) events (delegation)
   * ========================================================= */
  sectionsEl.addEventListener("click", (e) => {
    const t = e.target;

    const imgEl = t?.closest?.(".jsManualImg");
    if (imgEl) {
      const blockEl = imgEl.closest(".manual-block");
      const url = toStr(blockEl?.dataset?.imageUrl) || toStr(imgEl.getAttribute("src"));
      if (url) openViewer(url);
      return;
    }

    const editTitleBtn = t?.closest?.(".btnEditSectionTitle");
    if (editTitleBtn) {
      const sectionEl = editTitleBtn.closest(".manual-section");
      if (sectionEl) beginSectionTitleEdit(sectionEl);
      return;
    }

    const delSectionBtn = t?.closest?.(".btnDeleteSection");
    if (delSectionBtn) {
      const sectionId = delSectionBtn.getAttribute("data-section-id") || delSectionBtn.closest(".manual-section")?.dataset?.sectionId;
      const sectionEl = delSectionBtn.closest(".manual-section");
      deleteSectionById(sectionId, sectionEl);
      return;
    }

    const addBtn = t?.closest?.(".btn-add-block");
    if (addBtn) {
      const sid = addBtn.getAttribute("data-section-id");
      if (isDigits(sid)) openForAdd(Number(sid));
      return;
    }

    const editBtn = t?.closest?.(".btn-edit-block");
    if (editBtn) {
      const blockEl = editBtn.closest(".manual-block");
      if (blockEl) openForEdit(blockEl);
      return;
    }

    const delBlockBtn = t?.closest?.(".btn-delete-block");
    if (delBlockBtn) {
      const blockId = delBlockBtn.getAttribute("data-block-id") || delBlockBtn.closest(".manual-block")?.dataset?.blockId;
      const blockEl = delBlockBtn.closest(".manual-block");
      deleteBlockById(blockId, blockEl);
      return;
    }
  });

  /* =========================================================
   * 9) +구역추가 (JSON)
   * ========================================================= */
  btnAddSection?.addEventListener("click", async () => {
    const manualId = toStr(btnAddSection.dataset.manualId);
    const url = toStr(btnAddSection.dataset.sectionAddUrl);

    if (!isDigits(manualId)) return alert("manual_id가 올바르지 않습니다.");
    if (!url) return alert("section_add_url이 없습니다. (data-section-add-url 확인)");

    btnAddSection.disabled = true;
    const oldText = btnAddSection.textContent;
    btnAddSection.textContent = "추가중...";

    try {
      const data = await postJson(url, { manual_id: Number(manualId) });
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

  /* =========================================================
   * 10) save add/edit (FormData: image 포함)
   * ========================================================= */
  btnSave.addEventListener("click", async () => {
    clearError();

    const addUrl = toStr(modalEl.dataset.addUrl);
    const updateUrl = toStr(modalEl.dataset.updateUrl);
    const manualId = toStr(modalEl.dataset.manualId);

    let html = "";
    try {
      html = toStr(ensureQuill().root.innerHTML);
    } catch (e) {
      return showError(e?.message || "편집기 초기화에 실패했습니다.");
    }

    const normalized = html.replace(/\s+/g, "").toLowerCase();
    if (!html || normalized === "<p><br></p>" || normalized === "<p></p>") {
      return showError("텍스트 내용을 입력해주세요.");
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

        const data = await postForm(addUrl, fd);
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

        const data = await postForm(updateUrl, fd);
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
    } catch (err) {
      console.error(err);
      showError(err?.message || "저장 중 오류가 발생했습니다.");
    } finally {
      btnSave.disabled = false;
      btnSave.textContent = oldText;
    }
  });

  /* =========================================================
   * 11) modal reset
   * ========================================================= */
  modalEl.addEventListener("hidden.bs.modal", () => {
    mode = "add";
    editingBlockId = null;
    currentSectionId = null;
    clearError();
    resetImageUI();
    try { ensureQuill().setContents([]); } catch (_) {}
    if (attachInput) attachInput.value = "";
  });
})();
