/**
 * django_ma/static/js/partner/manage_table.js
 * ✅ Table Management (Final Refactor)
 * ------------------------------------------------------------
 * 목표
 * - mainTable: DataTables 사용 금지(정책 유지), Sortable 제거(▲/▼)
 * - rateUserTable: DataTables가 있으면 사용, 없으면 plain render fallback
 * - 엑셀: 다운로드 / 업로드 / ✅ 업로드 양식 다운로드(정적 템플릿)
 * - superuser: 검색 버튼 기반 조회 / main_admin: 자동조회
 * - URL/CSRF/브랜치 결정 로직 통일
 * - ✅ $ is not defined 완전 차단: jQuery 접근은 hasDT() 내부에서만
 * - 중복 바인딩 방지 + 오류 내성 강화
 * ------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("manage-table");
  if (!root) return;

  // ✅ 중복 로드 방지
  if (root.dataset.inited === "1") return;
  root.dataset.inited = "1";

  /* ---------------------------------------------------------
   * DOM refs
   * --------------------------------------------------------- */
  const els = {
    part: document.getElementById("partSelect"),
    branch: document.getElementById("branchSelect"),
    btnSearch: document.getElementById("btnSearch"),

    btnAdd: document.getElementById("btnAddRow"),
    btnSave: document.getElementById("btnSave"),
    btnReset: document.getElementById("btnReset"),
    btnToggleEdit: document.getElementById("btnToggleEdit"),

    btnDownloadExcel: document.getElementById("btnDownloadExcel"),
    btnUploadExcel: document.getElementById("btnUploadExcel"),
    btnDownloadTemplate: document.getElementById("btnDownloadTemplate"),

    inputExcel: document.getElementById("rateExcelInput"),

    tableBody: document.getElementById("tableBody"),
    overlay: document.getElementById("loadingOverlay"),

    rateUserTable: document.getElementById("rateUserTable"),
  };

  const userGrade = String(root.dataset.userGrade || "").trim();
  const userBranch = String(root.dataset.branch || "").trim();

  let editMode = false;
  let dtInstance = null; // rateUserTable DataTable instance cache

  /* ---------------------------------------------------------
   * Helpers
   * --------------------------------------------------------- */
  function showLoading(msg = "처리 중...") {
    if (!els.overlay) return;
    const label = els.overlay.querySelector(".mt-2");
    if (label) label.textContent = msg;
    els.overlay.hidden = false;
  }

  function hideLoading() {
    if (!els.overlay) return;
    els.overlay.hidden = true;
  }

  function alertBox(msg) {
    window.alert(msg);
  }

  function getCSRF() {
    return (
      window.csrfToken ||
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
      document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
      ""
    );
  }

  function enc(v) {
    return encodeURIComponent(v ?? "");
  }

  function isSuper() {
    return userGrade === "superuser";
  }

  function isMain() {
    return userGrade === "main_admin";
  }

  function resolveBranchFromUI() {
    // superuser: 셀렉트 / main_admin: userBranch / 그 외: 빈값
    if (isSuper()) return String(els.branch?.value || "").trim();
    if (isMain()) return userBranch;
    return "";
  }

  function urls() {
    const tableFetch = String(root.dataset.fetchUrl || "").trim();
    const tableSave = String(root.dataset.saveUrl || "").trim();

    // ✅ 템플릿: 정적 파일(dataset 우선) → 없으면 고정 경로 fallback
    const rateTemplateStatic =
      String(root.dataset.rateTemplateUrl || "").trim() ||
      "/static/excel/%EC%96%91%EC%8B%9D_%ED%85%8C%EC%9D%B4%EB%B8%94%EA%B4%80%EB%A6%AC.xlsx";

    return {
      tableFetch,
      tableSave,

      rateList: "/partner/ajax/rate-userlist/",
      rateExcel: "/partner/ajax/rate-userlist-excel/",
      rateUpload: "/partner/ajax/rate-userlist-upload/",

      // ✅ 양식 다운로드(정적 파일)
      rateTemplate: rateTemplateStatic,
    };
  }

  function hasJQ() {
    return typeof window.jQuery === "function" && typeof window.$ === "function";
  }

  function hasDT() {
    // ✅ $ 접근은 여기서만
    return hasJQ() && !!(window.$.fn && window.$.fn.DataTable);
  }

  /* ---------------------------------------------------------
   * ✅ DataTables 전역 차단(mainTable 정책 유지)
   * - DataTables가 로드되어도 mainTable에는 적용 안 되게 함
   * - ✅ DT가 없으면 아무 것도 하지 않음 ($ 접근 금지)
   * --------------------------------------------------------- */
  function blockDataTablesOnMainTable() {
    if (!hasDT()) return;

    const $ = window.$;

    // 혹시 기존 init된 DT가 있으면 제거(안전)
    try {
      $("table").each(function () {
        if ($.fn.DataTable.isDataTable(this)) {
          $(this).DataTable().destroy(true);
        }
      });
    } catch (_) {}

    $.fn.dataTable.ext.errMode = "none";

    const originalDT = $.fn.DataTable;
    $.fn.DataTable = function (...args) {
      if (this.attr("id") === "mainTable") return this; // mainTable DT 금지
      return originalDT.apply(this, args);
    };
  }

  /* ---------------------------------------------------------
   * Init
   * --------------------------------------------------------- */
  blockDataTablesOnMainTable();
  bindGlobalClickDelegation();
  bindTopButtons();
  bindRateCellGuards();

  // ✅ main_admin 자동조회
  if (isMain() && userBranch) {
    setTimeout(() => {
      const b = resolveBranchFromUI();
      if (!b) return;
      fetchTables(b);
      loadRateUserTable(b);
    }, 250);
  }

  // ✅ superuser 검색조회
  if (isSuper() && els.btnSearch) {
    els.btnSearch.addEventListener("click", () => {
      const b = resolveBranchFromUI();
      if (!b) return alertBox("지점을 선택해주세요.");
      fetchTables(b);
      loadRateUserTable(b);
    });
  }

  /* ---------------------------------------------------------
   * Bind: 상단 버튼(엑셀 포함)
   * --------------------------------------------------------- */
  function bindTopButtons() {
    // ✅ 수정모드 토글
    els.btnToggleEdit?.addEventListener("click", () => {
      editMode = !editMode;
      els.btnToggleEdit.textContent = editMode ? "읽기 모드 전환" : "수정 모드 전환";

      document.querySelectorAll("#mainTable .editable").forEach((td) => {
        td.contentEditable = String(editMode);
      });

      document
        .querySelectorAll("#mainTable .btnDeleteRow, #mainTable .btnMoveUp, #mainTable .btnMoveDown")
        .forEach((btn) => {
          const isDelete = btn.classList.contains("btnDeleteRow");
          btn.disabled = !editMode || (isDelete && userGrade === "sub_admin");
        });
    });

    // ✅ 행 추가
    els.btnAdd?.addEventListener("click", () => {
      const b = resolveBranchFromUI();
      if (!b) return alertBox("지점을 먼저 선택해주세요.");

      const order = (els.tableBody?.querySelectorAll("tr.data-row")?.length || 0) + 1;
      const tr = document.createElement("tr");
      tr.className = "data-row";
      tr.dataset.order = String(order);
      tr.innerHTML = `
        <td class="order-cell">${order}</td>
        <td>${escapeHtml(b)}</td>
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
        </td>
      `;
      els.tableBody?.appendChild(tr);
      updateOrderNumbers();
    });

    // ✅ 저장
    els.btnSave?.addEventListener("click", async () => {
      const b = resolveBranchFromUI();
      if (!b) return alertBox("지점 정보가 없습니다.");

      const u = urls();
      if (!u.tableSave) return alertBox("saveUrl이 설정되지 않았습니다.(data-save-url)");

      const rows = collectMainRows().filter((r) => r.table && r.rate && r.rate !== "%");
      if (rows.length === 0) return alertBox("저장할 데이터가 없습니다.");

      showLoading("저장 중...");
      try {
        const res = await fetch(u.tableSave, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ branch: b, rows }),
        });

        const data = await safeJson(res);
        if (data?.status === "success") {
          alertBox(`저장 완료 (${rows.length}건)`);
          await fetchTables(b);
        } else {
          throw new Error(data?.message || "저장 실패");
        }
      } catch (err) {
        alertBox("저장 중 오류 발생: " + err.message);
      } finally {
        hideLoading();
      }
    });

    // ✅ 초기화(재조회)
    els.btnReset?.addEventListener("click", async () => {
      const b = resolveBranchFromUI();
      if (!b) return alertBox("지점을 먼저 선택해주세요.");
      if (!confirm("테이블을 초기화(재조회)하시겠습니까?")) return;
      await fetchTables(b);
    });

    // ✅ 엑셀 다운로드(요율현황)
    els.btnDownloadExcel?.addEventListener("click", () => {
      const b = resolveBranchFromUI();
      if (!b) return alertBox("지점을 먼저 선택해주세요.");
      const u = urls();
      window.location.href = `${u.rateExcel}?branch=${enc(b)}`;
    });

    // ✅ 양식 다운로드(정적 파일)
    els.btnDownloadTemplate?.addEventListener("click", () => {
      const u = urls();
      if (!u.rateTemplate) return alertBox("양식 파일 경로가 설정되지 않았습니다.");
      window.location.href = u.rateTemplate;
    });

    // ✅ 엑셀 업로드
    if (els.btnUploadExcel && els.inputExcel) {
      els.btnUploadExcel.addEventListener("click", () => els.inputExcel.click());

      els.inputExcel.addEventListener("change", async (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;

        if (!confirm("선택한 엑셀의 '업로드' 시트를 기준으로 요율현황을 갱신하시겠습니까?")) {
          els.inputExcel.value = "";
          return;
        }

        const b = resolveBranchFromUI();
        if (!b) {
          els.inputExcel.value = "";
          return alertBox("지점을 먼저 선택해주세요.");
        }

        const u = urls();

        const formData = new FormData();
        formData.append("excel_file", file);
        formData.append("branch", b);
        formData.append("csrfmiddlewaretoken", getCSRF());

        showLoading("업로드 중...");
        try {
          const res = await fetch(u.rateUpload, {
            method: "POST",
            body: formData,
          });

          const data = await safeJson(res);
          if (data?.status === "success") {
            alertBox(data.message || "업로드 완료");
            await loadRateUserTable(b);
          } else {
            throw new Error(data?.message || "업로드 실패");
          }
        } catch (err) {
          alertBox("엑셀 업로드 중 오류 발생: " + err.message);
        } finally {
          hideLoading();
          els.inputExcel.value = "";
        }
      });
    }
  }

  /* ---------------------------------------------------------
   * MainTable 수집/렌더
   * --------------------------------------------------------- */
  function collectMainRows() {
    const rows = Array.from(els.tableBody?.querySelectorAll("tr.data-row") || []);
    return rows.map((tr) => {
      const tds = tr.querySelectorAll("td");
      return {
        order: parseInt(tr.dataset.order || "0", 10) || 0,
        branch: (tds[1]?.textContent || "").trim(),
        table: (tds[2]?.textContent || "").trim(),
        rate: (tds[3]?.textContent || "").trim(),
      };
    });
  }

  function renderMainTable(rows = [], branch) {
    if (!els.tableBody) return;
    els.tableBody.innerHTML = "";

    const safeRows = rows && rows.length ? rows : [{ order: 1, branch, table: "", rate: "" }];

    safeRows.forEach((r, idx) => {
      const order = r.order || idx + 1;
      const tr = document.createElement("tr");
      tr.className = "data-row";
      tr.dataset.order = String(order);

      tr.innerHTML = `
        <td class="order-cell">${order}</td>
        <td>${escapeHtml((r.branch || branch || "").trim())}</td>
        <td class="editable" contenteditable="${editMode}">${escapeHtml(r.table || "")}</td>
        <td class="editable rate-cell" contenteditable="${editMode}">${escapeHtml(r.rate || "")}</td>
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

  function updateOrderNumbers() {
    const rows = els.tableBody?.querySelectorAll("tr.data-row") || [];
    rows.forEach((row, idx) => {
      row.dataset.order = String(idx + 1);
      const cell = row.querySelector(".order-cell");
      if (cell) cell.textContent = String(idx + 1);
    });
  }

  /* ---------------------------------------------------------
   * 이벤트 위임: ▲/▼/삭제
   * --------------------------------------------------------- */
  function bindGlobalClickDelegation() {
    document.addEventListener("click", (e) => {
      if (!editMode) return;

      const upBtn = e.target.closest(".btnMoveUp");
      const downBtn = e.target.closest(".btnMoveDown");
      const delBtn = e.target.closest(".btnDeleteRow");

      if (upBtn) {
        const row = upBtn.closest("tr");
        const prev = row?.previousElementSibling;
        if (row && prev) row.parentNode.insertBefore(row, prev);
        updateOrderNumbers();
        return;
      }

      if (downBtn) {
        const row = downBtn.closest("tr");
        const next = row?.nextElementSibling;
        if (row && next) next.after(row);
        updateOrderNumbers();
        return;
      }

      if (delBtn) {
        if (!confirm("해당 행을 삭제하시겠습니까?")) return;
        delBtn.closest("tr")?.remove();
        updateOrderNumbers();
        return;
      }
    });
  }

  /* ---------------------------------------------------------
   * rate-cell 입력 제약(0~100, % 유지)
   * --------------------------------------------------------- */
  function bindRateCellGuards() {
    if (!els.tableBody) return;

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

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function safeJson(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`서버 응답이 JSON이 아닙니다. (status=${res.status})`);
    }
  }

  /* ---------------------------------------------------------
   * ✅ TableSetting 조회(fetch)
   * --------------------------------------------------------- */
  async function fetchTables(branch) {
    if (!branch) return;

    const u = urls();
    if (!u.tableFetch) return alertBox("fetchUrl이 설정되지 않았습니다.(data-fetch-url)");

    showLoading("데이터 불러오는 중...");
    try {
      const res = await fetch(`${u.tableFetch}?branch=${enc(branch)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await safeJson(res);

      const rows = data?.status === "success" ? (data.rows || []) : [];
      renderMainTable(rows, branch);
    } catch (err) {
      alertBox("데이터 조회 오류: " + err.message);
      renderMainTable([], branch);
    } finally {
      hideLoading();
    }
  }

  /* ---------------------------------------------------------
   * ✅ RateUserList 조회
   * - DataTables 있으면 DT로 렌더
   * - 없으면 plain tbody 렌더
   * - ✅ $ is not defined 방지: hasDT() 아닐 땐 절대 $ 접근 없음
   * --------------------------------------------------------- */
  async function loadRateUserTable(branch) {
    if (!branch || !els.rateUserTable) return;

    // 1) 데이터 fetch
    let payload;
    try {
      const u = urls();
      const res = await fetch(`${u.rateList}?branch=${enc(branch)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      payload = await safeJson(res);
    } catch (err) {
      console.error("요율현황 로드 실패(fetch)", err);
      // fetch 실패 시에도 테이블은 비우기
      renderRateUserPlain([]);
      return;
    }

    const rows = Array.isArray(payload?.data) ? payload.data : [];

    // 2) DataTables 사용 가능하면 DT로
    if (hasDT()) {
      const $ = window.$;

      // 기존 instance 있으면 destroy
      try {
        if (dtInstance && typeof dtInstance.destroy === "function") {
          dtInstance.destroy(true);
          dtInstance = null;
        }
      } catch (_) {}

      dtInstance = $("#rateUserTable").DataTable({
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

      dtInstance.clear();
      rows.forEach((u) => {
        dtInstance.row.add([
          u.branch || "",
          u.team_a || "",
          u.team_b || "",
          u.team_c || "",
          u.name || "",
          u.id || "",
          u.non_life_table || "",
          u.life_table || "",
        ]);
      });
      dtInstance.draw();
      return;
    }

    // 3) fallback: plain render
    renderRateUserPlain(rows);
  }

  function renderRateUserPlain(rows) {
    const tbody = els.rateUserTable?.querySelector("tbody");
    if (!tbody) return;

    tbody.innerHTML = "";
    rows.forEach((u) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(u.branch || "")}</td>
        <td>${escapeHtml(u.team_a || "")}</td>
        <td>${escapeHtml(u.team_b || "")}</td>
        <td>${escapeHtml(u.team_c || "")}</td>
        <td>${escapeHtml(u.name || "")}</td>
        <td>${escapeHtml(u.id || "")}</td>
        <td>${escapeHtml(u.non_life_table || "")}</td>
        <td>${escapeHtml(u.life_table || "")}</td>
      `;
      tbody.appendChild(tr);
    });
  }
});
