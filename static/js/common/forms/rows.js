/**
 * django_ma/static/js/common/forms/rows.js
 * ------------------------------------------------------------
 * ✅ 행 제어 유틸 (show/hide 방식)
 * - hiddenCount 기반으로 "다음 행 표시"
 * - reset: 첫 행 제외 모두 숨김 + 입력값 초기화
 * - remove: 특정 행 숨김 + 입력값 초기화
 *
 * ⚠️ 가정:
 * - rowSelector로 잡히는 row들이 초기부터 DOM에 존재하고
 *   "display: none"으로 숨겨졌다가 표시되는 구조
 * ------------------------------------------------------------
 */

import { qs, qsa, safeOn } from "./dom.js";

function clearInputs(row) {
  if (!row) return;
  row.querySelectorAll("input, textarea, select").forEach((el) => {
    // checkbox/radio는 checked 처리
    const t = (el.type || "").toLowerCase();
    if (t === "checkbox" || t === "radio") el.checked = false;
    else el.value = "";
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function isHiddenByDisplay(row) {
  // 기존 코드 호환: display:none 기반
  return row && row.style && row.style.display === "none";
}

function setDisplay(row, visible) {
  if (!row) return;
  row.style.display = visible ? "" : "none";
}

export function initRowController({
  rowSelector,
  addBtnId,
  resetBtnId,
  removeBtnClass, // 예: "btn-remove" (class명만)
  maxCount = 5,
  alertMsg = "최대 개수를 초과했습니다.",
  // remove 전략:
  // - "delegation": document에 위임(동적 버튼/행에 강함)
  // - "direct": 현재 존재하는 remove 버튼만 바인딩
  removeMode = "delegation",
  // 특정 row를 찾는 방식:
  // - support_form처럼 data-index가 있는 경우를 대비해 selector를 제공 가능
  resolveRowForRemove = null, // (btn) => rowElement
}) {
  const addBtn = qs(`#${addBtnId}`);
  const resetBtn = qs(`#${resetBtnId}`);

  const getRows = () => qsa(rowSelector);

  // ➕ 행 추가
  safeOn(addBtn, "click", () => {
    const rows = getRows();
    const hiddenRows = rows.filter((r) => isHiddenByDisplay(r));

    if (!hiddenRows.length) {
      window.alert(alertMsg);
      return;
    }

    // maxCount 방어 (DOM row가 더 많아도 maxCount까지만 허용)
    const visibleCount = rows.length - hiddenRows.length;
    if (visibleCount >= maxCount) {
      window.alert(alertMsg);
      return;
    }

    setDisplay(hiddenRows[0], true);
  });

  // ♻️ 초기화
  safeOn(resetBtn, "click", () => {
    const rows = getRows();
    rows.forEach((r, idx) => {
      setDisplay(r, idx === 0);
      clearInputs(r);
    });
  });

  // ❌ 제거
  const doRemove = (btn) => {
    const row =
      typeof resolveRowForRemove === "function"
        ? resolveRowForRemove(btn)
        : btn?.closest?.(rowSelector);

    if (!row) return;

    setDisplay(row, false);
    clearInputs(row);
  };

  if (removeMode === "direct") {
    // 현재 있는 버튼만 바인딩
    qsa(`.${removeBtnClass}`).forEach((btn) => safeOn(btn, "click", () => doRemove(btn)));
  } else {
    // 권장: 이벤트 위임 (동적으로 생성/표시되는 버튼에도 안전)
    document.addEventListener("click", (e) => {
      const btn = e.target?.closest?.(`.${removeBtnClass}`);
      if (!btn) return;
      doRemove(btn);
    });
  }
}
