// django_ma/static/js/commission/approval_excel_upload.js
(() => {
  const form = document.getElementById("approvalExcelUploadForm");
  const resultEl = document.getElementById("approvalUploadResult");
  const toastEl = document.getElementById("approvalUploadToast");
  const modalEl = document.getElementById("approvalExcelUploadModal");

  if (!form) return;

  const getCSRFToken = () => {
    const inp = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  };

  const setSubmitting = (on) => {
    form.dataset.submitting = on ? "1" : "0";
    const btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = on;
  };

  const showResult = (msg, type = "muted") => {
    if (!resultEl) return;
    resultEl.textContent = msg;
    resultEl.className = `mt-3 small text-center text-${type}`;
  };

  const showToast = () => {
    if (toastEl && window.bootstrap) {
      const toast = new bootstrap.Toast(toastEl, { delay: 1800 });
      toast.show();
    }
  };

  const closeModal = () => {
    if (!modalEl || !window.bootstrap) return;
    const inst = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    inst.hide();
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (form.dataset.submitting === "1") return;

    setSubmitting(true);
    showResult("업로드 중...", "muted");

    const fd = new FormData(form);

    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: fd,
      });

      const data = await res.json().catch(() => null);

      if (!res.ok || !data || data.ok !== true) {
        const msg = (data && data.message) ? data.message : "업로드 실패";
        showResult(msg, "danger");
        return;
      }

      // ✅ 성공 메시지(삽입건수까지 표시)
      const inserted = (typeof data.inserted === "number") ? data.inserted : null;
      const info = inserted !== null
        ? `✅ 완료 (${data.ym} / ${data.kind}) · rows: ${data.row_count} · 반영: ${inserted}`
        : `✅ 완료 (${data.ym} / ${data.kind}) · rows: ${data.row_count}`;

      showResult(info, "success");
      showToast();

      // ✅ 모달 닫고, 화면을 새로고침해서 테이블에 반영된 데이터 표시
      setTimeout(() => {
        closeModal();
        // 현재 쿼리스트링(year/month/part) 유지한 채로 reload
        window.location.reload();
      }, 600);

    } catch (err) {
      showResult("⚠️ 네트워크 오류로 업로드에 실패했습니다.", "danger");
    } finally {
      setSubmitting(false);
    }
  });
})();
