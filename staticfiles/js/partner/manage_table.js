/**
 * ✅ 테이블 관리 페이지 (v4.3)
 * ------------------------------------------------------------
 * - DataTables 완전 차단 (다른 페이지 영향 없음)
 * - 드래그앤드롭 제거 → ▲ / ▼ 버튼으로 순서 조정
 * - ↓ 버튼 정상 작동 (아래로 이동)
 * - 요율 입력: 정수만 (0~100), 자동 %
 * - 빈칸은 저장 제외
 * - ✅ 요율현황 : superuser는 검색 버튼 클릭 시, main_admin은 자동조회
 * ------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("manage-table");
  if (!root) return;

  /* ---------------------------------------------------------
     ✅ DataTables 전역 차단 (이 페이지 전용)
     --------------------------------------------------------- */
  if (window.jQuery && $.fn.DataTable) {
    $("table").each(function () {
      if ($.fn.DataTable.isDataTable(this)) {
        $(this).DataTable().destroy();
      }
    });

    // 자동 초기화 차단
    $.fn.dataTable.ext.errMode = "none";
    const originalDT = $.fn.DataTable;
    $.fn.DataTable = function (...args) {
      if (this.attr("id") === "mainTable") return this; // 이 페이지의 메인 테이블은 차단
      return originalDT.apply(this, args);
    };
  }

  /* ---------------------------------------------------------
     요소 및 전역 변수
  --------------------------------------------------------- */
  const els = {
    part: document.getElementById("partSelect"),
    branch: document.getElementById("branchSelect"),
    btnSearch: document.getElementById("btnSearch"),
    btnAdd: document.getElementById("btnAddRow"),
    btnSave: document.getElementById("btnSave"),
    btnReset: document.getElementById("btnReset"),
    btnToggleEdit: document.getElementById("btnToggleEdit"),
    tableBody: document.getElementById("tableBody"),
    overlay: document.getElementById("loadingOverlay"),
  };

  const userGrade = root.dataset.userGrade;
  const userBranch = root.dataset.branch;
  let editMode = false;

  const showLoading = (msg = "처리 중...") => {
    const label = els.overlay?.querySelector(".mt-2");
    if (label) label.textContent = msg;
    els.overlay.hidden = false;
  };
  const hideLoading = () => (els.overlay.hidden = true);
  const getCSRF = () =>
    window.csrfToken ||
    document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    "";
  const alertBox = (msg) => window.alert(msg);

  /* ---------------------------------------------------------
     초기 실행
  --------------------------------------------------------- */
  init();

  function init() {
    // ✅ main_admin은 페이지 진입 시 자동 조회 (테이블 + 요율현황)
    if (userGrade === "main_admin" && userBranch) {
      setTimeout(() => {
        fetchData(userBranch);
        loadRateUserTable(userBranch);
      }, 300);
    }

    // ✅ superuser는 검색 버튼 클릭 시 조회
    if (userGrade === "superuser" && els.btnSearch) {
      els.btnSearch.addEventListener("click", () => {
        const branch = els.branch.value?.trim();
        if (!branch) return alertBox("지점을 선택해주세요.");
        fetchData(branch);
        loadRateUserTable(branch);
      });
    }

    bindRateEvents();
  }

  /* ---------------------------------------------------------
     요율 입력 처리 (0~100, 자동 %)
  --------------------------------------------------------- */
  function bindRateEvents() {
    els.tableBody.addEventListener(
      "focus",
      (e) => {
        const cell = e.target.closest(".rate-cell");
        if (!cell || !editMode) return;
        let val = cell.textContent.trim();
        if (!val) {
          cell.textContent = "%";
          placeCaretAtStart(cell);
        } else if (!val.endsWith("%")) {
          cell.textContent = val + "%";
          placeCaretBeforePercent(cell);
        }
      },
      true
    );

    els.tableBody.addEventListener("input", (e) => {
      const cell = e.target.closest(".rate-cell");
      if (!cell || !editMode) return;
      let num = cell.textContent.replace(/[^0-9]/g, "");
      if (num === "") num = "0";
      let intVal = parseInt(num, 10);
      if (isNaN(intVal)) intVal = 0;
      if (intVal > 100) intVal = 100;
      cell.textContent = intVal + "%";
      placeCaretBeforePercent(cell);
    });

    els.tableBody.addEventListener(
      "blur",
      (e) => {
        const cell = e.target.closest(".rate-cell");
        if (!cell || !editMode) return;
        let val = cell.textContent.trim();
        if (val === "%") cell.textContent = "";
        else if (!val.endsWith("%")) {
          let n = parseInt(val.replace(/[^0-9]/g, ""), 10);
          if (isNaN(n) || n < 0) n = 0;
          if (n > 100) n = 100;
          cell.textContent = n + "%";
        }
      },
      true
    );
  }

  function placeCaretBeforePercent(el) {
    const sel = window.getSelection();
    const range = document.createRange();
    const textNode = el.firstChild;
    if (!textNode) return;
    const pos = Math.max(0, textNode.length - 1);
    range.setStart(textNode, pos);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function placeCaretAtStart(el) {
    const sel = window.getSelection();
    const range = document.createRange();
    const textNode = el.firstChild;
    if (!textNode) return;
    range.setStart(textNode, 0);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  /* ---------------------------------------------------------
     데이터 조회
  --------------------------------------------------------- */
  async function fetchData(branch) {
    if (!branch) return;
    showLoading("데이터 불러오는 중...");
    const url = `${root.dataset.fetchUrl}?branch=${encodeURIComponent(branch)}`;
    try {
      const res = await fetch(url);
      const data = await res.json();
      renderTable(data.status === "success" ? data.rows || [] : [], branch);
    } catch (err) {
      alertBox("데이터 조회 오류: " + err.message);
    } finally {
      hideLoading();
    }
  }

  /* ---------------------------------------------------------
     테이블 렌더링
  --------------------------------------------------------- */
  function renderTable(rows = [], branch) {
    els.tableBody.innerHTML = "";
    if (!rows.length) rows = [{ order: 1, branch, table: "", rate: "" }];

    rows.forEach((r, idx) => {
      const order = r.order || idx + 1;
      const tr = document.createElement("tr");
      tr.className = "data-row";
      tr.dataset.order = order;
      tr.innerHTML = `
        <td class="order-cell">${order}</td>
        <td>${r.branch || branch}</td>
        <td class="editable" contenteditable="${editMode}">${r.table || ""}</td>
        <td class="editable rate-cell" contenteditable="${editMode}">${r.rate || ""}</td>
        <td>
          <button class="btn btn-outline-secondary btn-sm btnMoveUp" ${!editMode ? "disabled" : ""}>▲</button>
          <button class="btn btn-outline-secondary btn-sm btnMoveDown" ${!editMode ? "disabled" : ""}>▼</button>
        </td>
        <td>
          <button class="btn btn-sm btn-danger btnDeleteRow" ${
            !editMode || userGrade === "sub_admin" ? "disabled" : ""
          }>삭제</button>
        </td>
      `;
      els.tableBody.appendChild(tr);
    });

    updateOrderNumbers();
  }

  /* ---------------------------------------------------------
     순번 재계산
  --------------------------------------------------------- */
  function updateOrderNumbers() {
    const rows = els.tableBody.querySelectorAll("tr.data-row");
    rows.forEach((row, idx) => {
      row.dataset.order = idx + 1;
      const cell = row.querySelector(".order-cell");
      if (cell) cell.textContent = idx + 1;
    });
  }

  /* ---------------------------------------------------------
     수정 모드
  --------------------------------------------------------- */
  els.btnToggleEdit?.addEventListener("click", () => {
    editMode = !editMode;
    els.btnToggleEdit.textContent = editMode ? "읽기 모드 전환" : "수정 모드 전환";
    document.querySelectorAll(".editable").forEach((td) => (td.contentEditable = editMode));
    document.querySelectorAll(".btnDeleteRow, .btnMoveUp, .btnMoveDown").forEach((btn) => {
      btn.disabled = !editMode || (btn.classList.contains("btnDeleteRow") && userGrade === "sub_admin");
    });
  });

  /* ---------------------------------------------------------
     행 이동 / 추가 / 삭제 / 저장 / 초기화
  --------------------------------------------------------- */
  document.addEventListener("click", (e) => {
    if (!editMode) return;
    const upBtn = e.target.closest(".btnMoveUp");
    const downBtn = e.target.closest(".btnMoveDown");
    const delBtn = e.target.closest(".btnDeleteRow");

    if (upBtn) {
      const row = upBtn.closest("tr");
      const prev = row.previousElementSibling;
      if (prev) row.parentNode.insertBefore(row, prev);
      updateOrderNumbers();
    }

    if (downBtn) {
      const row = downBtn.closest("tr");
      const next = row.nextElementSibling;
      if (next) next.after(row);
      updateOrderNumbers();
    }

    if (delBtn) {
      if (!confirm("해당 행을 삭제하시겠습니까?")) return;
      delBtn.closest("tr")?.remove();
      updateOrderNumbers();
    }
  });

  els.btnAdd?.addEventListener("click", () => {
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    if (!branch) return alertBox("지점을 먼저 선택해주세요.");
    const order = els.tableBody.querySelectorAll("tr.data-row").length + 1;
    const tr = document.createElement("tr");
    tr.className = "data-row";
    tr.dataset.order = order;
    tr.innerHTML = `
      <td class="order-cell">${order}</td>
      <td>${branch}</td>
      <td class="editable" contenteditable="${editMode}"></td>
      <td class="editable rate-cell" contenteditable="${editMode}">%</td>
      <td>
        <button class="btn btn-outline-secondary btn-sm btnMoveUp" ${!editMode ? "disabled" : ""}>▲</button>
        <button class="btn btn-outline-secondary btn-sm btnMoveDown" ${!editMode ? "disabled" : ""}>▼</button>
      </td>
      <td>
        <button class="btn btn-sm btn-danger btnDeleteRow" ${
          !editMode || userGrade === "sub_admin" ? "disabled" : ""
        }>삭제</button>
      </td>`;
    els.tableBody.appendChild(tr);
    updateOrderNumbers();
  });

  els.btnSave?.addEventListener("click", async () => {
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    if (!branch) return alertBox("지점 정보가 없습니다.");
    const rows = Array.from(els.tableBody.querySelectorAll("tr.data-row"))
      .map((tr) => {
        const tds = tr.querySelectorAll("td");
        return {
          order: parseInt(tr.dataset.order, 10),
          branch: tds[1].textContent.trim(),
          table: tds[2].textContent.trim(),
          rate: tds[3].textContent.trim(),
        };
      })
      .filter((r) => r.table && r.rate && r.rate !== "%");

    if (rows.length === 0) return alertBox("저장할 데이터가 없습니다.");

    showLoading("저장 중...");
    try {
      const res = await fetch(root.dataset.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({ branch, rows }),
      });
      const data = await res.json();
      if (data.status === "success") {
        alertBox(`저장 완료 (${rows.length}건)`);
        await fetchData(branch);
      } else {
        throw new Error(data.message || "저장 실패");
      }
    } catch (err) {
      alertBox("저장 중 오류 발생: " + err.message);
    } finally {
      hideLoading();
    }
  });

  els.btnReset?.addEventListener("click", async () => {
    if (!confirm("테이블을 초기화하시겠습니까?")) return;
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    await fetchData(branch);
  });

  // ------------------------------------------------------------
  // ✅ 지점 내 사용자 요율현황 테이블 로드
  // ------------------------------------------------------------
  async function loadRateUserTable(branch) {
    if (!branch) return;
    const table = $("#rateUserTable").DataTable({
      destroy: true,
      searching: true,
      paging: true,
      pageLength: 10,
      lengthChange: true,
      order: [[0, "asc"]],
      info: false,
      language: {
        lengthMenu: "_MENU_개씩 보기",
        search: "검색:",
        zeroRecords: "데이터가 없습니다.",
        infoEmpty: "데이터 없음",
        paginate: { next: "다음", previous: "이전" },
      },
    });

    try {
      const res = await fetch(`/partner/ajax/rate-userlist/?branch=${encodeURIComponent(branch)}`);
      const data = await res.json();
      table.clear();
      data.data.forEach((u) => {
        table.row.add([
          u.name || "",
          u.id || "",
          u.branch || "",
          u.team_a || "",
          u.team_b || "",
          u.team_c || "",
          u.non_life_table || "",
          u.life_table || "",
        ]);
      });
      table.draw();
    } catch (err) {
      console.error("요율현황 로드 실패", err);
    }
  }
});
