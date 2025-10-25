/**
 * manage_grades.js
 * ---------------------------------------------------
 * 권한관리 페이지용 JS
 * 1. DataTables 중복 초기화 방지
 * 2. 열 개수 자동 검증
 * 3. 엑셀 업로드 자동 처리
 * 4. Export 버튼
 * ---------------------------------------------------
 */

document.addEventListener('DOMContentLoaded', function () {
  const tableEl = document.getElementById('mainTable');
  const uploadBtn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('excelFile');
  const form = document.getElementById('excelUploadForm');

  /* =======================================================
     ⚡ 1. 테이블 구조 자동 검증 (th ↔ td 일치)
  ======================================================= */
  if (tableEl) {
    const thCount = tableEl.querySelectorAll('thead th').length;
    const firstRow = tableEl.querySelector('tbody tr');
    const tdCount = firstRow ? firstRow.querySelectorAll('td').length : 0;

    if (thCount !== tdCount) {
      console.warn(
        `⚠️ [DataTables Skip] 헤더(${thCount})와 바디(${tdCount}) 열 개수가 다릅니다. DataTables 초기화를 건너뜁니다.`
      );
      return; // 열 불일치 시 DataTables 초기화 중단
    }

    /* =======================================================
       ⚡ 2. 기존 초기화 제거 (Cannot reinitialise 방지)
    ======================================================= */
    if ($.fn.dataTable.isDataTable(tableEl)) {
      $(tableEl).DataTable().clear().destroy();
    }

    /* =======================================================
       ⚡ 3. DataTables 초기화
    ======================================================= */
    $(tableEl).DataTable({
      responsive: true,
      autoWidth: false,
      pageLength: 25,
      order: [],
      language: {
        url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/ko.json',
      },
      dom: 'Bfrtip',
      buttons: [
        {
          extend: 'excel',
          text: '<i class="bi bi-download"></i> 엑셀 다운로드',
          className: 'btn btn-outline-success btn-sm mb-2',
          exportOptions: { columns: ':visible' },
        },
      ],
    });
  }

  /* =======================================================
     ⚡ 4. 엑셀 업로드 자동 처리
  ======================================================= */
  if (uploadBtn && fileInput && form) {
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (!fileInput.files.length) return;
      const fileName = fileInput.files[0].name;
      if (confirm(`"${fileName}" 파일을 업로드하여 데이터를 수정/추가하시겠습니까?`)) {
        form.submit();
      } else {
        fileInput.value = '';
      }
    });
  }
});
