// ✅ datatable_config.js — 공용 DataTables 초기화 스크립트 (Export 기능 포함)
document.addEventListener("DOMContentLoaded", function() {
  const tables = document.querySelectorAll(".datatable");
  if (!tables.length) return;

  tables.forEach(table => {
    const enableColumnFilter = table.dataset.columnFilter === "true";
    const enableExport = table.dataset.export === "true";

    // ✅ DataTable 기본 설정
    const dt = $(table).DataTable({
      language: {
        url: "//cdn.datatables.net/plug-ins/1.13.8/i18n/ko.json"
      },
      paging: true,
      searching: true,
      ordering: true,
      order: [],
      lengthMenu: [10, 25, 50, 100],
      pageLength: 25,
      responsive: true,
      autoWidth: false,
      dom: enableExport ? 'Bfrtip' : 'frtip', // ✅ export 버튼 활성화 여부
      buttons: enableExport ? [
        {
          extend: 'excelHtml5',
          text: '엑셀 다운로드',
          className: 'btn btn-sm btn-primary'
        }
      ] : []
    });

    // ✅ 엑셀처럼 컬럼별 검색 필터 추가
    if (enableColumnFilter) {
      $(table).find("thead th").each(function() {
        const title = $(this).text();
        $(this).html(title + '<br><input type="text" class="form-control form-control-sm" placeholder="검색" />');
      });

      dt.columns().every(function() {
        const that = this;
        $("input", this.header()).on("keyup change", function() {
          if (that.search() !== this.value) {
            that.search(this.value).draw();
          }
        });
      });
    }
  });
});
