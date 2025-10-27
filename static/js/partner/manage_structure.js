/**
 * manage_structure.js (리팩토링 버전)
 * -----------------------------------------------------
 * 편제변경(Manage Structure) 페이지 전용 스크립트
 * 기능:
 * 1. 데이터 조회 (fetch)
 * 2. 데이터 저장 / 삭제 (Ajax)
 * 3. 기한 설정
 * 4. 입력 가능 여부 제어
 * 5. 초기 상태별 동작(main_admin 자동조회 / superuser 수동조회)
 * -----------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("manage-structure");
  if (!root) return;

  /* =======================================================
     📌 기본 요소 참조
  ======================================================= */
  const els = {
    year: document.getElementById("yearSelect"),
    month: document.getElementById("monthSelect"),
    branch: document.getElementById("branchSelect"),
    deadline: document.getElementById("deadlineSelect"),
    btnSearch: document.getElementById("btnSearchPeriod"),
    btnDeadline: document.getElementById("btnSetDeadline"),
    inputSection: document.getElementById("inputSection"),
    btnAddRow: document.getElementById("btnAddRow"),
    btnResetRows: document.getElementById("btnResetRows"),
    btnSaveRows: document.getElementById("btnSaveRows"),
    inputTable: document.getElementById("inputTable"),
    mainTable: document.getElementById("mainTable"),
    loading: document.getElementById("loadingOverlay"),
  };

  const { userGrade, dataFetchUrl, dataSaveUrl, dataDeleteUrl, setDeadlineUrl } =
    root.dataset;

  /* =======================================================
     📌 공통 유틸 함수
  ======================================================= */
  const showLoading = (msg = "처리 중...") => {
    els.loading.querySelector(".mt-2").textContent = msg;
    els.loading.hidden = false;
  };
  const hideLoading = () => (els.loading.hidden = true);
  const alertBox = (msg) => alert(msg);

  const getCSRFToken = () => {
    return window.csrfToken || (document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "");
  };

  const pad2 = (n) => (String(n).length === 1 ? "0" + n : String(n));
  const selectedYM = () => `${els.year.value}-${pad2(els.month.value)}`;

  /* =======================================================
     📌 1. 기본 Select 옵션 세팅
  ======================================================= */
  const now = new Date();
  const [thisY, thisM] = [now.getFullYear(), now.getMonth() + 1];

  for (let y = thisY - 2; y <= thisY + 1; y++) {
    els.year.insertAdjacentHTML(
      "beforeend",
      `<option value="${y}" ${y === thisY ? "selected" : ""}>${y}년</option>`
    );
  }
  for (let m = 1; m <= 12; m++) {
    els.month.insertAdjacentHTML(
      "beforeend",
      `<option value="${m}" ${m === thisM ? "selected" : ""}>${m}월</option>`
    );
  }
  if (els.deadline) {
    for (let d = 1; d <= 31; d++) {
      els.deadline.insertAdjacentHTML("beforeend", `<option value="${d}">${d}일</option>`);
    }
  }

  /* =======================================================
     📌 2. 데이터 조회
  ======================================================= */
  async function fetchData() {
    const y = els.year.value;
    const m = els.month.value;
    const b = els.branch?.value || "";
    const ym = `${y}-${pad2(m)}`;

    if (userGrade === "superuser" && !b) return alertBox("부서를 선택해주세요.");

    showLoading("데이터 불러오는 중...");
    try {
      const res = await fetch(`${dataFetchUrl}?month=${ym}&branch=${b}`);
      if (!res.ok) throw new Error("조회 실패");
      const data = await res.json();
      renderMainTable(data.rows || []);
    } catch (err) {
      console.error(err);
      alertBox("데이터를 불러오지 못했습니다.");
    } finally {
      hideLoading();
    }
  }

  function renderMainTable(rows) {
    const tbody = els.mainTable.querySelector("tbody");
    tbody.innerHTML = "";

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="16" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
      return;
    }

    rows.forEach((r) => {
      tbody.insertAdjacentHTML(
        "beforeend",
        `
        <tr>
          <td>${r.requester_name || "-"}</td>
          <td>${r.requester_id || "-"}</td>
          <td>${r.branch || "-"}</td>
          <td>${r.target_name || "-"}</td>
          <td>${r.target_id || "-"}</td>
          <td>${r.target_branch || "-"}</td>
          <td>${r.chg_branch || "-"}</td>
          <td>${r.rank || "-"}</td>
          <td>${r.chg_rank || "-"}</td>
          <td>${r.table_name || "-"}</td>
          <td>${r.rate || "-"}</td>
          <td>${r.chg_table || "-"}</td>
          <td>${r.chg_rate || "-"}</td>
          <td>${r.memo || "-"}</td>
          <td>${r.request_date || "-"}</td>
          <td>${r.process_date || "-"}</td>
          <td><button class="btn btn-outline-danger btn-sm btnDeleteRow" data-id="${r.id}">삭제</button></td>
        </tr>`
      );
    });
    attachDeleteHandlers();
  }

  els.btnSearch?.addEventListener("click", fetchData);

  /* =======================================================
     📌 3. 데이터 저장
  ======================================================= */
  async function saveRows() {
    const rows = Array.from(els.inputTable.querySelectorAll("tbody tr")).map((tr) => {
      const obj = {};
      tr.querySelectorAll("input, select").forEach((el) => {
        obj[el.name] = el.type === "checkbox" ? el.checked : el.value.trim();
      });
      return obj;
    });

    showLoading("저장 중...");
    try {
      const res = await fetch(dataSaveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ rows, month: selectedYM() }),
      });
      const data = await res.json();
      alertBox(data.message || "저장 완료");
      if (data.status === "success") fetchData();
    } catch (err) {
      console.error(err);
      alertBox("저장 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  }

  els.btnSaveRows?.addEventListener("click", saveRows);

  /* =======================================================
     📌 4. 데이터 삭제
  ======================================================= */
  function attachDeleteHandlers() {
    document.querySelectorAll(".btnDeleteRow").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("이 항목을 삭제하시겠습니까?")) return;
        showLoading("삭제 중...");
        try {
          const res = await fetch(dataDeleteUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({ id: btn.dataset.id }),
          });
          const data = await res.json();
          alertBox(data.message || "삭제 완료");
          if (data.status === "success") fetchData();
        } catch (err) {
          console.error(err);
          alertBox("삭제 중 오류 발생");
        } finally {
          hideLoading();
        }
      })
    );
  }

  /* =======================================================
     📌 5. 입력기한 설정
  ======================================================= */
  els.btnDeadline?.addEventListener("click", async () => {
    const branch = els.branch?.value || "";
    const day = els.deadline?.value || "";
    if (!branch || !day) return alertBox("부서와 기한을 선택해주세요.");

    showLoading("기한 설정 중...");
    try {
      const res = await fetch(setDeadlineUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ branch, deadline_day: day, month: selectedYM() }),
      });
      const data = await res.json();
      alertBox(data.message || "기한 설정 완료");

      if (data.status === "success") {
        window.ManageStructureBoot.deadlineDay = parseInt(day);
        checkInputAvailability();
      }
    } catch (err) {
      console.error(err);
      alertBox("기한 설정 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  });

  /* =======================================================
     📌 6. 입력 가능 여부 제어
  ======================================================= */
  function checkInputAvailability() {
    const inputSection = document.getElementById("inputSection");
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth() + 1;

    // 선택 연/월
    const selectedYear = parseInt(yearSelect.value);
    const selectedMonth = parseInt(monthSelect.value);
    const deadlineDay = window.ManageStructureBoot.deadlineDay || 10;
    const effectiveDeadline = parseInt(deadlineDay);

    // 초기 표시
    inputSection.removeAttribute("hidden");

    let reason = "";
    if (selectedYear < currentYear || (selectedYear === currentYear && selectedMonth < currentMonth)) {
      reason = "과거월은 입력 불가";
    } else if (selectedYear === currentYear && selectedMonth === currentMonth && today.getDate() > effectiveDeadline) {
      reason = `입력기한(${effectiveDeadline}일) 경과`;
    }

    if (reason) {
      inputSection.classList.add("disabled-mode");
      inputSection.querySelectorAll("input, select, button").forEach(el => el.disabled = true);
    } else {
      inputSection.classList.remove("disabled-mode");
      inputSection.querySelectorAll("input, select, button").forEach(el => el.disabled = false);
    }
  }

  /* =======================================================
     📌 7. 초기 동작
  ======================================================= */
  if (window.jQuery && $.fn.DataTable) {
    $(els.mainTable).DataTable({
      language: { search: "검색 :", lengthMenu: "표시 _MENU_ 개" },
      order: [],
    });
  }

  // main_admin → 자동조회 / superuser → 대기
  if (userGrade === "main_admin") setTimeout(fetchData, 300);

  // ✅ 항상 대상자 입력 섹션 표시 (디버그용)
  els.inputSection.removeAttribute("hidden");
});
