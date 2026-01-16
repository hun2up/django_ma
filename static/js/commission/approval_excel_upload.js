// django_ma/static/js/commission/approval_excel_upload.js
(() => {
  "use strict";

  const form = document.getElementById("approvalExcelUploadForm");
  if (!form) return;

  const resultEl = document.getElementById("approvalUploadResult");
  const toastEl = document.getElementById("approvalUploadToast");
  const modalEl = document.getElementById("approvalExcelUploadModal");

  // ===== utils =====
  const $ = (sel, root = document) => root.querySelector(sel);

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
    if (!toastEl || !window.bootstrap) return;
    const toast = new bootstrap.Toast(toastEl, { delay: 1800 });
    toast.show();
  };

  const closeModal = () => {
    if (!modalEl || !window.bootstrap) return;
    const inst =
      bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    inst.hide();
  };

  const readSelectValue = (selectorList) => {
    for (const sel of selectorList) {
      const el = $(sel, form) || $(sel);
      if (!el) continue;
      const v = (el.value ?? "").toString().trim();
      if (v) return v;
    }
    return "";
  };

  const readFileInput = (selectorList) => {
    for (const sel of selectorList) {
      const el = $(sel, form) || $(sel);
      if (!el) continue;
      if (el.files && el.files.length > 0) return el;
    }
    return null;
  };

  const validate = ({ year, month, kind, fileEl }) => {
    if (!year) return { ok: false, msg: "연도를 선택해주세요." };
    if (!month) return { ok: false, msg: "월도를 선택해주세요." };
    // ✅ part는 '전체' 업로드도 가능하므로 필수 체크 제거
    if (!kind) return { ok: false, msg: "구분을 선택해주세요." };
    if (!fileEl) return { ok: false, msg: "엑셀 파일을 선택해주세요." };

    const file = fileEl.files[0];
    const name = (file?.name || "").toLowerCase();

    const okExt = name.endsWith(".xlsx") || name.endsWith(".xls");
    if (!okExt) {
      return { ok: false, msg: "엑셀 파일(.xlsx / .xls)만 업로드할 수 있습니다." };
    }
    return { ok: true, msg: "" };
  };


  const buildSuccessMessage = (data) => {
    const ym = data?.ym ? String(data.ym) : "-";
    const kind = data?.kind ? String(data.kind) : "-";
    const rowCount = typeof data?.row_count === "number" ? data.row_count : null;
    const inserted = typeof data?.inserted === "number" ? data.inserted : null;

    const parts = [`✅ 완료 (${ym} / ${kind})`];
    if (rowCount !== null) parts.push(`rows: ${rowCount}`);
    if (inserted !== null) parts.push(`반영: ${inserted}`);
    return parts.join(" · ");
  };

  // ===== main submit handler =====
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (form.dataset.submitting === "1") return;

    // (중요) 템플릿 id/name이 바뀌어도 최대한 살아남게 selector 여러 개 지원
    const year = readSelectValue(['select[name="year"]', "#year", "#approvalYear"]);
    const month = readSelectValue(['select[name="month"]', "#month", "#approvalMonth"]);
    const part = readSelectValue(['select[name="part"]', "#part", "#approvalPart"]);
    const kind = readSelectValue(['select[name="kind"]', "#kind", "#approvalKind"]);

    const fileEl = readFileInput([
      'input[type="file"][name="excel_file"]',
      'input[type="file"][name="file"]',
      'input[type="file"]#excel_file',
      'input[type="file"]#approvalExcelFile',
      'input[type="file"]',
    ]);

    const v = validate({ year, month, part, kind, fileEl });
    if (!v.ok) {
      showResult(v.msg, "danger");
      return;
    }

    setSubmitting(true);
    showResult("업로드 중...", "muted");

    // ✅ FormData 구성 + 값 강제 set (name 누락/폼 밖 배치/브라우저 이슈 대비)
    const fd = new FormData(form);
    fd.set("year", year);
    fd.set("month", month);
    fd.set("part", part);
    fd.set("kind", kind);

    // 파일 name이 다른 경우도 대비해서 excel_file 키로 통일(서버가 excel_file 기대 시)
    // 이미 excel_file로 들어있다면 그대로고, 아니면 강제로 추가
    if (!fd.get("excel_file") && fileEl?.files?.[0]) {
      fd.set("excel_file", fileEl.files[0]);
    }

    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: fd,
      });

      const data = await res.json().catch(() => null);

      if (!res.ok || !data || data.ok !== true) {
        const msg =
          (data && data.message) ? data.message : `업로드 실패 (HTTP ${res.status})`;
        showResult(msg, "danger");
        return;
      }

      showResult(buildSuccessMessage(data), "success");
      showToast();

      // ✅ 모달 닫고, 쿼리스트링 유지한 채 새로고침
      setTimeout(() => {
        closeModal();
        window.location.reload();
      }, 600);

    } catch (err) {
      showResult("⚠️ 네트워크 오류로 업로드에 실패했습니다.", "danger");
    } finally {
      setSubmitting(false);
    }
  });
})();
