/**
 * manage_grades.js
 * ---------------------------------------------------
 * 권한관리 페이지 전용 스크립트
 * 기능:
 * 1. DataTables 중복 초기화 방지 및 안전 검증
 * 2. 빈 테이블 시 placeholder 자동 추가
 * 3. 열 개수 불일치 방지 및 경고 무시 설정
 * 4. 엑셀 업로드 자동 처리
 * 5. Export 버튼
 * ---------------------------------------------------
 */

document.addEventListener('DOMContentLoaded', () => {
  const tableEl = document.getElementById('mainTable');
  const uploadBtn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('excelFile');
  const form = document.getElementById('excelUploadForm');

  /** =======================================================
   * ⚙️ 0. DataTables 전역 에러 무시 설정
   * (Incorrect column count 등의 경고창 차단)
   ======================================================= */
  $.fn.dataTable.ext.errMode = 'none';

  /** =======================================================
   * 📘 1. 테이블 구조 점검 및 placeholder 삽입
   ======================================================= */
  const ensureTableStructure = (table) => {
    const thCount = table.querySelectorAll('thead th').length;
    const tbody = table.querySelector('tbody');
    let firstRow = tbody.querySelector('tr');
    let tdCount = firstRow ? firstRow.querySelectorAll('td').length : 0;

    // ✅ 빈 tbody이거나 colspan 구조인 경우 안전하게 placeholder 생성
    if (!firstRow || tdCount < thCount) {
      console.warn('⚠️ 테이블 데이터 없음 — placeholder 행 자동 생성');
      tbody.innerHTML = '';
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.setAttribute('colspan', thCount);
      cell.classList.add('text-center', 'text-muted');
      cell.innerHTML = '추가된 중간관리자가 없습니다.<br>중간관리자 추가는 부서장에게 문의해주세요.';
      row.appendChild(cell);
      tbody.appendChild(row);
      tdCount = thCount;
    }

    return { thCount, tdCount };
  };

  /** =======================================================
   * 📘 2. DataTables 초기화 (중복 방지)
   ======================================================= */
  const initDataTable = (table) => {
    if ($.fn.dataTable.isDataTable(table)) {
      $(table).DataTable().clear().destroy();
    }

    $(table).DataTable({
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
          className: 'btn btn-success btn-sm',
          exportOptions: { columns: ':visible' },
        },
      ],
    });
  };

  /** =======================================================
   * 📘 3. 엑셀 업로드 자동 처리
   ======================================================= */
  const initExcelUpload = () => {
    if (!uploadBtn || !fileInput || !form) return;
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (!fileInput.files.length) return;
      const fileName = fileInput.files[0].name;
      const confirmMsg = `"${fileName}" 파일을 업로드하여 데이터를 수정/추가하시겠습니까?`;
      if (confirm(confirmMsg)) form.submit();
      else fileInput.value = '';
    });
  };

  /** =======================================================
   * 📘 4. 실행 흐름
   ======================================================= */
  if (tableEl) {
    const { thCount, tdCount } = ensureTableStructure(tableEl);

    if (thCount !== tdCount) {
      console.warn(
        `⚠️ [DataTables Skip] 헤더(${thCount})와 바디(${tdCount}) 열 개수가 다릅니다. DataTables 초기화를 건너뜁니다.`
      );
    } else {
      initDataTable(tableEl);
    }
  }

  initExcelUpload();
});
