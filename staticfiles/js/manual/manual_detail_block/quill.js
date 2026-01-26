// django_ma/static/js/manual/manual_detail_block/quill.js
// -----------------------------------------------------------------------------
// Quill manager (Minimal split)
// - ensureQuill()
// - 첨부 업로드 + 링크 삽입
// - getHtml / setHtml / reset / onModalShown
// -----------------------------------------------------------------------------

export function createQuillManager({ S, modalEl, errBox, attachInput, api, state, formatBytes }) {
  const { toStr, clearErrorBox, showErrorBox } = S;

  let quill = null;

  function err(msg) {
    showErrorBox(errBox, msg, false);
  }

  function ensureQuill() {
    if (quill) return quill;
    if (typeof window.Quill === "undefined") throw new Error("Quill이 로드되지 않았습니다.");

    quill = new window.Quill("#manualQuillEditor", {
      theme: "snow",
      modules: {
        toolbar: {
          container: [
            [{ header: [1, 2, 3, false] }],
            ["bold", "italic", "underline", "strike"],
            [{ color: [] }, { background: [] }],
            [{ align: [] }, { indent: "-1" }, { indent: "+1" }],
            [{ list: "ordered" }, { list: "bullet" }],
            ["link", "attach"],
            ["clean"],
          ],
          handlers: {
            attach: () => {
              clearErrorBox(errBox);

              if (!attachInput) return err("첨부 입력 요소가 없습니다. (#manualQuillAttachInput)");
              if (state.mode !== "edit" || !state.editingBlockId) {
                return err("첨부는 '먼저 저장된 블록'에서만 가능합니다. 저장 후 '수정'에서 첨부해주세요.");
              }
              attachInput.value = "";
              attachInput.click();
            },
          },
        },
      },
    });

    // attach 버튼 아이콘 부여(기존 유지)
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

  function onModalShown() {
    try {
      ensureQuill().update("silent");
    } catch (e) {
      err(e?.message);
    }
  }

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
    if (!state.editingBlockId || state.mode !== "edit") {
      throw new Error("첨부는 '저장된 블록'에서만 가능합니다. 먼저 블록을 저장한 뒤, 수정에서 첨부해주세요.");
    }

    const fd = new FormData();
    fd.append("block_id", String(state.editingBlockId));
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

  function getHtml() {
    return ensureQuill().root.innerHTML;
  }

  function setHtml(html) {
    const q = ensureQuill();
    const safe = toStr(html || "");
    try {
      if (!safe) q.setContents([]);
      else q.clipboard.dangerouslyPasteHTML(safe);
    } catch (_) {
      // Quill clipboard 오류 방어
      q.setContents([]);
    }
  }

  function reset() {
    try {
      ensureQuill().setContents([]);
    } catch (_) {}
  }

  return { ensureQuill, onModalShown, getHtml, setHtml, reset };
}
