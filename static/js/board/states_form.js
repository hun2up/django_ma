/**
 * django_ma/static/js/board/states_form.js
 * ------------------------------------------------------------
 * ✅ FA 소명서 페이지 전용 스크립트 (Board)
 * 기능:
 * - 계약사항 행 추가/초기화/제거
 * - 보험료 입력: 숫자만 + 콤마 / submit 시 콤마 제거
 * - PDF 생성: POST(FormData) → Blob 다운로드
 *
 * 요구 요소(id):
 * - requestForm
 * - loadingOverlay
 * - generatePdfBtn (data-pdf-url 필요)
 * - addContractBtn / resetContractBtn
 *
 * 요구 행 구조:
 * - .contract-row 들이 DOM에 미리 존재 (숨김: style.display="none")
 * - 제거 버튼은 class "btn-remove"를 가짐
 * ------------------------------------------------------------
 */

import { qs } from "../common/forms/dom.js";
import { initRowController } from "../common/forms/rows.js";
import { bindPremiumInputs } from "../common/forms/premium.js";

function getCsrfToken() {
  return (
    window.csrfToken ||
    document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    ""
  );
}

async function downloadPdf({ url, formEl, filename }) {
  const formData = new FormData(formEl);
  const csrf = getCsrfToken();

  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: csrf ? { "X-CSRFToken": csrf } : {},
    credentials: "same-origin",
  });

  if (!res.ok) throw new Error(`PDF 생성 실패 (HTTP ${res.status})`);

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename || "download.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(objectUrl);
}

document.addEventListener("DOMContentLoaded", () => {
  const form = qs("#requestForm");
  const overlay = qs("#loadingOverlay");
  const generateBtn = qs("#generatePdfBtn");

  if (!form || !generateBtn) return;

  // 1) 계약사항 행 제어
  initRowController({
    rowSelector: ".contract-row",
    addBtnId: "addContractBtn",
    resetBtnId: "resetContractBtn",
    removeBtnClass: "btn-remove",
    maxCount: 5,
    alertMsg: "계약사항은 최대 5개까지만 입력 가능합니다.",
    removeMode: "delegation", // 동적/숨김 행에도 안전
  });

  // 2) 보험료 입력 처리
  bindPremiumInputs({ formEl: form, inputSelector: 'input[name^="premium_"]' });

  // 3) PDF 생성
  generateBtn.addEventListener("click", async () => {
    const pdfUrl = generateBtn.dataset.pdfUrl;
    if (!pdfUrl) return window.alert("PDF URL(data-pdf-url)이 없습니다.");

    // overlay 표시 (기존 템플릿이 display 기반이면 유지)
    if (overlay) overlay.style.display = "flex";

    try {
      await downloadPdf({
        url: pdfUrl,
        formEl: form,
        filename: "FA_소명서.pdf",
      });
    } catch (err) {
      console.error(err);
      window.alert("PDF 생성 중 오류가 발생했습니다.");
    } finally {
      if (overlay) overlay.style.display = "none";
    }
  });
});
