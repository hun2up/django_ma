// django_ma/static/js/partner/manage_table.js
/**
 * ✅ 테이블 관리 페이지 (수정 완료 버전)
 * ------------------------------------------------------------
 * ✅ superuser: 부서/지점 선택 후 검색 가능
 * ✅ main_admin: 자동 조회 (setTimeout)
 * ✅ DataTables 충돌 방지 (destroy 후 재생성)
 * ✅ 오류 메시지 상세 출력
 * ------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("manage-table");
  if (!root) return;

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
  let table = null;

  /* =======================================================
     📘 유틸 함수
  ======================================================= */
  const showLoading = (msg = "처리 중...") => {
    const label = els.overlay.querySelector(".mt-2");
    if (label) label.textContent = msg;
    els.overlay.hidden = false;
  };
  const hideLoading = () => (els.overlay.hidden = true);

  const getCSRF = () => {
    if (window.csrfToken) return window.csrfToken;
    const tokenInput = document.querySelector("[name=csrfmiddlewaretoken]");
    if (tokenInput) return tokenInput.value;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };
  const alertBox = (msg) => window.alert(msg);

  /* =======================================================
     📘 초기 실행
  ======================================================= */
  init();

  async function init() {
    if (userGrade === "main_admin") {
      console.log("🟢 main_admin 모드 → 자동조회 실행 (0.3s delay)");
      setTimeout(() => fetchData(userBranch), 300);
    } else if (userGrade === "superuser") {
      console.log("🟦 superuser 모드 → 부서/지점 선택 후 검색 대기");
      els.btnSearch?.addEventListener("click", () => {
        const branch = els.branch.value;
        if (!branch) return alertBox("지점을 선택해주세요.");
        fetchData(branch);
      });
    } else {
      console.log("🚫 sub_admin 접근 차단 (서버단 제한)");
    }
  }

  /* =======================================================
     📘 데이터 조회
  ======================================================= */
  async function fetchData(branch) {
    if (!branch) return;
    showLoading("데이터 불러오는 중...");

    const url = `${root.dataset.fetchUrl}?branch=${encodeURIComponent(branch)}`;
    try {
      console.log("📡 fetchData 호출:", url);
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        console.log(`✅ ${branch} 지점 데이터 ${data.rows.length}건`);
        renderTable(data.rows || [], branch);
      } else {
        console.warn("⚠️ 서버 응답 상태:", data.status);
        renderTable([], branch);
      }
    } catch (err) {
      console.error("❌ fetchData 오류:", err.message, err.stack);
      alertBox("서버 오류 또는 일시적인 문제입니다.\n(" + err.message + ")");
    } finally {
      hideLoading();
    }
  }

  /* =======================================================
     📘 테이블 렌더링 (DataTables 충돌 방지)
  ======================================================= */
  function renderTable(rows = [], branch) {
    const $table = $("#mainTable");

    if (!rows.length) rows = [{ branch, table: "", rate: "" }];

    // ✅ 기존 DataTable이 있다면 제거 후 재생성
    if ($.fn.DataTable.isDataTable($table)) {
      $table.DataTable().clear().destroy();
    }

    const body = $table.find("tbody");
    body.empty();

    rows.forEach((r) => {
      body.append(`
        <tr class="data-row">
          <td>${r.branch || branch}</td>
          <td class="editable" contenteditable="${editMode}">${r.table || ""}</td>
          <td class="editable" contenteditable="${editMode}">${r.rate || ""}</td>
          <td>
            <button class="btn btn-sm btn-danger btnDeleteRow" ${
              !editMode || userGrade === "sub_admin" ? "disabled" : ""
            }>삭제</button>
          </td>
        </tr>
      `);
    });

    table = $table.DataTable({
      paging: true,
      searching: true,
      ordering: true,
      info: false,
      language: {
        search: "검색:",
        lengthMenu: "_MENU_ 개씩 보기",
        zeroRecords: "데이터 없음",
        paginate: { previous: "이전", next: "다음" },
      },
    });
    hideLoading();
  }

  /* =======================================================
     📘 수정 모드 전환
  ======================================================= */
  els.btnToggleEdit?.addEventListener("click", () => {
    editMode = !editMode;
    els.btnToggleEdit.textContent = editMode ? "읽기 모드 전환" : "수정 모드 전환";
    document.querySelectorAll(".editable").forEach((td) => (td.contentEditable = editMode));
    document.querySelectorAll(".btnDeleteRow").forEach(
      (btn) => (btn.disabled = !editMode || userGrade === "sub_admin")
    );
  });

  /* =======================================================
     📘 행 추가 / 삭제
  ======================================================= */
  els.btnAdd?.addEventListener("click", () => {
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    if (!branch) return alertBox("지점을 먼저 선택해주세요.");

    const tr = document.createElement("tr");
    tr.className = "data-row";
    tr.innerHTML = `
      <td>${branch}</td>
      <td class="editable" contenteditable="${editMode}"></td>
      <td class="editable" contenteditable="${editMode}"></td>
      <td>
        <button class="btn btn-sm btn-danger btnDeleteRow" ${
          !editMode || userGrade === "sub_admin" ? "disabled" : ""
        }>삭제</button>
      </td>`;
    els.tableBody.appendChild(tr);
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btnDeleteRow");
    if (!btn) return;
    const tr = btn.closest("tr");
    if (confirm("해당 행을 삭제하시겠습니까?")) tr.remove();
  });

  /* =======================================================
     📘 저장
  ======================================================= */
  els.btnSave?.addEventListener("click", async () => {
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    if (!branch) return alertBox("지점 정보가 없습니다.");

    const rows = Array.from(els.tableBody.querySelectorAll("tr.data-row")).map((tr) => {
      const tds = tr.querySelectorAll("td");
      return {
        branch: tds[0].textContent.trim(),
        table: tds[1].textContent.trim(),
        rate: tds[2].textContent.trim(),
      };
    });

    showLoading("저장 중...");
    try {
      const payload = { rows, branch };
      console.log("💾 저장 요청:", payload);

      const res = await fetch(root.dataset.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRF(),
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        alertBox(`저장 완료 (${data.saved_count || rows.length}건)`);
        await fetchData(branch);
      } else {
        throw new Error(data.message || "저장 실패");
      }
    } catch (err) {
      console.error("❌ save error:", err);
      alertBox("저장 중 오류 발생 (" + err.message + ")");
    } finally {
      hideLoading();
    }
  });

  /* =======================================================
     📘 초기화
  ======================================================= */
  els.btnReset?.addEventListener("click", async () => {
    if (!confirm("테이블을 초기화하시겠습니까?")) return;
    const branch = userGrade === "superuser" ? els.branch.value : userBranch;
    await fetchData(branch);
  });
});
