// django_ma/static/js/partner/manage_rate/dom_refs.js

export const els = {
  // rate 전용 루트 (없으면 구조 재사용 위해 structure도 한 번 더 탐색)
  root:
    document.getElementById("manage-rate") ||
    document.getElementById("manage-structure"),

  // 상단 컨트롤 박스
  yearSelect: document.getElementById("yearSelect"),
  monthSelect: document.getElementById("monthSelect"),
  partSelect: document.getElementById("partSelect"),
  branchSelect: document.getElementById("branchSelect"),
  btnSearch: document.getElementById("btnSearchPeriod"),

  // 카드 안 테이블
  inputTable: document.getElementById("inputTable"),
  mainTable: document.getElementById("mainTable"),

  // 공용 로딩 오버레이
  loadingOverlay: document.getElementById("loadingOverlay"),
};
