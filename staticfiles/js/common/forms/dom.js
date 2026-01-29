/**
 * django_ma/static/js/common/forms/dom.js
 * ------------------------------------------------------------
 * ✅ 공통 DOM 유틸
 * - qs / qsa
 * - safeOn (요소 존재할 때만 이벤트 바인딩)
 * - show/hide (hidden 속성 기반)
 * ------------------------------------------------------------
 */

export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function safeOn(el, eventName, handler, options) {
  if (!el) return false;
  el.addEventListener(eventName, handler, options);
  return true;
}

export function show(el) {
  if (!el) return;
  el.hidden = false;
}

export function hide(el) {
  if (!el) return;
  el.hidden = true;
}
