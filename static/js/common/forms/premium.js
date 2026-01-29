/**
 * django_ma/static/js/common/forms/premium.js
 * ------------------------------------------------------------
 * ✅ 보험료 입력 공통 처리
 * - 입력 시 숫자만 허용 + 천단위 콤마
 * - paste 방어
 * - submit 직전 콤마 제거 (서버에는 숫자만)
 * ------------------------------------------------------------
 */

import { qsa } from "./dom.js";

function onlyDigits(s) {
  return String(s ?? "").replace(/[^0-9]/g, "");
}

function withComma(numStr) {
  const digits = onlyDigits(numStr);
  if (!digits) return "";
  return Number(digits).toLocaleString("ko-KR");
}

export function bindPremiumInputs({
  formEl,
  inputSelector = 'input[name^="premium_"]',
  removeCommaOnSubmit = true,
} = {}) {
  const inputs = qsa(inputSelector);

  inputs.forEach((input) => {
    input.addEventListener("input", (e) => {
      e.target.value = withComma(e.target.value);
    });

    input.addEventListener("paste", (e) => {
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData)?.getData("text") || "";
      e.target.value = withComma(text);
    });
  });

  if (removeCommaOnSubmit && formEl) {
    formEl.addEventListener("submit", () => {
      inputs.forEach((input) => {
        input.value = onlyDigits(input.value);
      });
    });
  }
}
