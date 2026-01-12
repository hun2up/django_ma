// django_ma/static/js/commission/approval_excel_upload.js
(() => {
  const form = document.getElementById("approvalExcelUploadForm");
  const resultEl = document.getElementById("approvalUploadResult");
  const toastEl = document.getElementById("approvalUploadToast");
  const modalEl = document.getElementById("approvalExcelUploadModal");

  if (!form || !resultEl) return;
  if (form.dataset.bound === "1") return;
  form.dataset.bound = "1";

  const submitBtn = form.querySelector('button[type="submit"]');

  const getCSRFToken = () => {
    const inp = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  };

  const setResult = (msg, kind = "muted") => {
    resultEl.textContent = msg || "";
    resultEl.className = `mt-3 small text-center text-${kind}`;
  };

  const setSubmitting = (on) => {
    form.dataset.submitting = on ? "1" : "0";

    // form 내 모든 input/select/file disable
    const fields = form.querySelectorAll("input, select, button");
    fields.forEach((el) => {
      // 취소 버튼은 막지 않아도 되지만, 업로드 중 모달 닫기 방지 원하면 disable 유지 가능
      if (el === submitBtn) return;
      el.disabled = !!on;
    });

    if (submitBtn) {
      submitBtn.disabled = !!on;
      submitBtn.textContent = on ? "업로드 중..." : "업로드";
    }
  };

  const showToast = () => {
    if (!toastEl || !window.bootstrap) return;
    try {
      const toast = new bootstrap.Toast(toastEl, { delay: 1800 });
      toast.show();
    } catch (_) {}
  };

  const closeModal = () => {
    if (!modalEl || !window.bootstrap) return;
    try {
      const inst = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      inst.hide();
    } catch (_) {}
  };

  const safeJson = async (res) => {
    try {
      return await res.json();
    } catch (_) {
      return null;
    }
  };

  const formatServerError = (data) => {
    if (!data) return "업로드 실패";

    let msg = data.message || "업로드 실패";

    // 컬럼 진단(views.py에서 detected_columns 내려주는 케이스)
    if (Array.isArray(data.detected_columns) && data.detected_columns.length) {
      const cols = data.detected_columns.slice(0, 25).join(", ");
      msg += `\n(감지된 컬럼 일부: ${cols}${data.detected_columns.length > 25 ? "..." : ""})`;
    }

    // 미매칭 샘플
    if (Array.isArray(data.missing_sample) && data.missing_sample.length) {
      msg += `\n(미매칭 사번 예시: ${data.missing_sample.slice(0, 10).join(", ")}${
        data.missing_sample.length > 10 ? "..." : ""
      })`;
    }

    return msg;
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (form.dataset.submitting === "1") return;

    setSubmitting(true);
    setResult("업로드 중...", "muted");

    const fd = new FormData(form);

    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: fd,
      });

      const data = await safeJson(res);

      if (!res.ok || !data || data.ok !== true) {
        const msg = formatServerError(data);
        // 줄바꿈 표현을 위해 textContent 사용(HTML X)
        setResult(msg, "danger");
        return;
      }

      // ✅ 성공 메시지 표준화
      const ym = data.ym || "-";
      const kind = data.kind || "-";
      const rows = typeof data.row_count === "number" ? data.row_count : (data.uploaded ?? "-");
      const info = `✅ 완료 (${ym} / ${kind}) · 반영: ${rows}건`;

      setResult(info, "success");
      showToast();

      // ✅ 모달 닫기 + 페이지 갱신(성공한 데이터 표시)
      //  - 지연을 주는 이유: 토스트/메시지를 잠깐 보여주기 위함
      setTimeout(() => {
        closeModal();
        // 필요한 경우: 업로드 결과 테이블 즉시 갱신
        window.location.reload();
      }, 500);

    } catch (err) {
      setResult("⚠️ 네트워크 오류로 업로드에 실패했습니다.", "danger");
    } finally {
      setSubmitting(false);
    }
  });
})();
