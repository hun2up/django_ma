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

function getPdfUrlFallback() {
  // 1) 버튼 dataset
  const btn = document.querySelector("#generatePdfBtn");
  const fromBtn = btn?.dataset?.pdfUrl;
  if (fromBtn) return fromBtn;
  // 2) 루트 div dataset
  const root = document.querySelector("#states-form");
  const fromRoot = root?.dataset?.pdfUrl;
  return fromRoot || "";
}

async function downloadPdf({ url, formEl, filename }) {
  const formData = new FormData(formEl);
  const csrf = getCsrfToken();

  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: {
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
      // ✅ 서버가 "fetch 호출"임을 확실히 인지하도록
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
  });

  if (!res.ok) {
    // ✅ 서버가 JSON 에러를 주는 경우 메시지 노출
    const ct0 = (res.headers.get("content-type") || "").toLowerCase();
    if (ct0.includes("application/json")) {
      try {
        const data = await res.json();
        throw new Error(data?.message || data?.error || `PDF 생성 실패 (HTTP ${res.status})`);
      } catch (_) {
        /* ignore */
      }
    }
    throw new Error(`PDF 생성 실패 (HTTP ${res.status})`);
  }

  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/json")) {
    // 서버에서 에러를 JSON으로 반환하는 경우(권한/검증 실패 등) 사용자에게 노출
    let msg = "PDF 생성 실패";
    try {
      const data = await res.json();
      msg = data?.message || data?.error || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  
   // ✅ PDF가 아닌 응답(redirect로 인한 HTML 등)이면 다운로드 시도 자체를 막음
  if (!ct.includes("application/pdf")) {
    let hint = "";
    try {
      const text = await res.text();
      hint = text?.slice?.(0, 200) || "";
    } catch (_) {}
    throw new Error("PDF 응답이 아닙니다. (서버가 리다이렉트/에러 페이지를 반환했을 수 있습니다.)" + (hint ? `\n\n${hint}` : ""));
  }

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
  // 템플릿이 premium1 / premium_1 둘 다 나올 수 있어 폭넓게 매칭
  bindPremiumInputs({
    formEl: form,
    inputSelector: 'input[name^="premium_"], input[name^="premium"]',
  });

  // 3) PDF 생성
  generateBtn.addEventListener("click", async () => {
    const pdfUrl = generateBtn.dataset.pdfUrl || getPdfUrlFallback();
    if (!pdfUrl) return window.alert("PDF URL(data-pdf-url)이 없습니다.");

    // overlay 표시 (기존 템플릿이 display 기반이면 유지)
    if (overlay) overlay.style.display = "flex"; // CSS가 flex 기준일 때 자연스러움

    try {
      await downloadPdf({
        url: pdfUrl,
        formEl: form,
        filename: "FA_소명서.pdf",
      });
    } catch (err) {
      console.error(err);
      window.alert(err?.message || "PDF 생성 중 오류가 발생했습니다.");
    } finally {
      if (overlay) overlay.style.display = "none";
    }
  });
});
