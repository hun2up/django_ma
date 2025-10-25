/**
 * manage_grades.js
 * ---------------------------------------------------
 * 권한관리 페이지 전용 스크립트 (상단 SubAdmin + 하단 AllUser)
 * 기능:
 * 1. DataTables 초기화 및 중복 방지
 * 2. 엑셀 업로드 자동 처리
 * 3. 인라인 수정 (팀A/B/C) — 양방향 실시간 동기화
 * 4. DataTables Ajax 모드에서도 이벤트 유지
 * ---------------------------------------------------
 */

document.addEventListener('DOMContentLoaded', () => {
  const tables = ['subAdminTable', 'allUserTable'];
  const uploadBtn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('excelFile');
  const form = document.getElementById('excelUploadForm');

  /* =======================================================
     ⚙️ 0. DataTables 경고 무시
  ======================================================= */
  $.fn.dataTable.ext.errMode = 'none';

  /* =======================================================
     📘 1. 엑셀 업로드 자동 처리
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

  /* =======================================================
     📘 2. 인라인 수정 (공통 함수)
  ======================================================= */
  function handleEditableCell(cell, tableId) {
    const row = cell.closest('tr');
    const userId = row.dataset.userId;
    const field = cell.dataset.field;
    const oldValue = cell.textContent.trim();

    if (!userId || cell.querySelector('input')) return;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldValue === '-' ? '' : oldValue;
    input.className = 'form-control form-control-sm';
    input.style.minWidth = '80px';
    input.style.fontSize = '13px';
    cell.textContent = '';
    cell.appendChild(input);
    input.focus();

    const saveChange = () => {
      const newValue = input.value.trim();
      if (newValue === oldValue) {
        cell.textContent = oldValue;
        return;
      }

      fetch('/partner/ajax/update-team/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          user_id: userId,
          field,
          value: newValue,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            cell.textContent = newValue || '-';
            cell.classList.add('bg-success-subtle');
            setTimeout(() => cell.classList.remove('bg-success-subtle'), 1000);

            // ✅ 상대 테이블에 즉시 반영
            const otherTableId =
              tableId === 'subAdminTable' ? 'allUserTable' : 'subAdminTable';
            const otherTable = document.getElementById(otherTableId);
            if (otherTable) {
              const targetRow = otherTable.querySelector(
                `tr[data-user-id="${userId}"]`
              );
              if (targetRow) {
                const targetCell = targetRow.querySelector(
                  `td[data-field="${field}"]`
                );
                if (targetCell) {
                  targetCell.textContent = newValue || '-';
                  targetCell.classList.add('bg-info-subtle');
                  setTimeout(() => targetCell.classList.remove('bg-info-subtle'), 1000);
                }
              }
            }
          } else {
            alert(`❌ 저장 실패: ${data.error}`);
            cell.textContent = oldValue;
          }
        })
        .catch((err) => {
          console.error('서버 오류:', err);
          cell.textContent = oldValue;
        });
    };

    input.addEventListener('blur', saveChange);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') input.blur();
      if (e.key === 'Escape') cell.textContent = oldValue;
    });
  }

  /* =======================================================
     📘 3. DataTables 초기화
  ======================================================= */
  if (!$.fn.DataTable.isDataTable('#allUserTable')) {
    $('#allUserTable').DataTable({
      serverSide: true,
      processing: true,
      ajax: {
        url: $('#allUserTable').data('ajax-url'),
        type: 'GET',
      },
      columns: [
        { data: 'part' },
        { data: 'branch' },
        { data: 'name' },
        { data: 'user_id' },
        { data: 'position' },
        {
          data: 'team_a',
          render: (d, t, r) => `<td class="editable" data-field="team_a">${d || '-'}</td>`,
        },
        {
          data: 'team_b',
          render: (d, t, r) => `<td class="editable" data-field="team_b">${d || '-'}</td>`,
        },
        {
          data: 'team_c',
          render: (d, t, r) => `<td class="editable" data-field="team_c">${d || '-'}</td>`,
        },
      ],
      createdRow: function (row, data) {
        row.dataset.userId = data.user_id;
      },
      pageLength: 10,
      language: {
        url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/ko.json',
      },
    });
  }

  /* =======================================================
     📘 4. 인라인 수정 이벤트 (양쪽 테이블 공통)
  ======================================================= */
  tables.forEach((id) => {
    const table = document.getElementById(id);
    if (!table) return;

    // ✅ DataTables Ajax 모드에도 대응하도록 위임
    table.addEventListener('click', (e) => {
      const cell = e.target.closest('td.editable');
      if (cell) handleEditableCell(cell, id);
    });
  });
});
