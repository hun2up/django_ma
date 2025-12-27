/**
 * django_ma/static/js/common/manage/csrf.js
 * ------------------------------------------------------------
 * - CSRF 토큰 공통 처리
 * ------------------------------------------------------------
 */

export function getCSRFToken() {
  return (
    window.csrfToken ||
    document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    ""
  );
}
