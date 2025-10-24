/**
 * manage_structure.js
 * -----------------------------------------------------
 * 편제변경(Manage Structure) 페이지 전용 스크립트
 * 기능:
 * 1. 월도 데이터 fetch() 연동
 * 2. 대상자 행 추가/초기화/저장(Ajax)
 * 3. 삭제/기한설정 Ajax
 * 4. DataTables 초기화
 * 5. 로딩/검증/중복사번 방지
 * 6. 기한 기본값(10일) + 입력제한/비활성화 표시
 * -----------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("manage-structure");
  if (!root) return;

  /* =======================================================
     📌 기본 DOM 요소
  ======================================================= */
  const yearSelect = document.getElementById("yearSelect");
  const monthSelect = document.getElementById("monthSelect");
  const branchSelect = document.getElementById("branchSelect");
  const deadlineSelect = document.getElementById("deadlineSelect");
  const btnSearchPeriod = document.getElementById("btnSearchPeriod");
  const btnSetDeadline = document.getElementById("btnSetDeadline");
  const inputSection = document.getElementById("inputSection");
  const btnAddRow = document.getElementById("btnAddRow");
  const btnResetRows = document.getElementById("btnResetRows");
  const btnSaveRows = document.getElementById("btnSaveRows");
  const inputTable = document.getElementById("inputTable");
  const mainTable = document.getElementById("mainTable");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const searchModal = document.getElementById("searchUserModal");
  const btnDoSearch = document.getElementById("btnDoSearch");
  const searchResults = document.getElementById("searchResults");

  const {
    userGrade,
    dataFetchUrl,
    dataSaveUrl,
    dataDeleteUrl,
    setDeadlineUrl,
  } = root.dataset;

  const showLoading = (msg = "처리 중...") => {
    loadingOverlay.querySelector(".mt-2").textContent = msg;
    loadingOverlay.hidden = false;
  };
  const hideLoading = () => (loadingOverlay.hidden = true);
  const alertBox = (msg) => alert(msg);

  /* =======================================================
     📌 1. 기초 셀렉트 옵션 생성
  ======================================================= */
  const now = new Date();
  const thisYear = now.getFullYear();
  const thisMonth = now.getMonth() + 1;

  for (let y = thisYear - 2; y <= thisYear + 1; y++) {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = `${y}년`;
    if (y === thisYear) opt.selected = true;
    yearSelect.appendChild(opt);
  }

  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = `${m}월`;
    if (m === thisMonth) opt.selected = true;
    monthSelect.appendChild(opt);
  }

  for (let d = 1; d <= 31; d++) {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = `${d}일`;
    deadlineSelect?.appendChild(opt);
  }

  /* =======================================================
     📌 2. 월도 선택 후 데이터 불러오기 (fetch)
  ======================================================= */
  async function fetchData() {
    const y = yearSelect.value;
    const m = monthSelect.value;
    const ym = `${y}-${m.padStart ? m.padStart(2, "0") : ("0" + m).slice(-2)}`;

    showLoading("데이터 불러오는 중...");

    try {
      const res = await fetch(`${dataFetchUrl}?month=${ym}`);
      if (!res.ok) throw new Error("데이터 조회 실패");
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
    const tbody = mainTable.querySelector("tbody");
    tbody.innerHTML = "";

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="13" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
      return;
    }

    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.requester_name || "-"}</td>
        <td>${r.requester_id || "-"}</td>
        <td>${r.branch || "-"}</td>
        <td>${r.target_name || "-"}</td>
        <td>${r.target_id || "-"}</td>
        <td>${r.target_branch || "-"}</td>
        <td>${r.chg_branch || "-"}</td>
        <td>${r.rank || "-"}</td>
        <td>${r.chg_rank || "-"}</td>
        <td>${r.memo || "-"}</td>
        <td>${r.request_date || "-"}</td>
        <td>${r.process_date || "-"}</td>
        <td><button class="btn btn-outline-danger btn-sm btnDeleteRow" data-id="${r.id}">삭제</button></td>
      `;
      tbody.appendChild(tr);
    });

    attachDeleteHandlers();
  }

  btnSearchPeriod?.addEventListener("click", fetchData);

  /* =======================================================
     📌 3. 데이터 저장 (ajax_save)
  ======================================================= */
  async function saveRows() {
    const rows = [...inputTable.querySelectorAll("tbody tr")].map((tr) => {
      const obj = {};
      tr.querySelectorAll("input,select").forEach((el) => {
        if (el.type === "checkbox") obj[el.name] = el.checked;
        else obj[el.name] = el.value.trim();
      });
      return obj;
    });

    const month = `${yearSelect.value}-${monthSelect.value.padStart ? monthSelect.value.padStart(2, "0") : ("0" + monthSelect.value).slice(-2)}`;

    showLoading("저장 중...");

    try {
      const res = await fetch(dataSaveUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() || document.querySelector('[name=csrfmiddlewaretoken]')?.value || "" },
        body: JSON.stringify({ rows, month }),
      });
      const data = await res.json();
      if (data.status === "success") {
        alertBox(data.message);
        fetchData();
      } else {
        alertBox(data.message);
      }
    } catch (err) {
      console.error(err);
      alertBox("저장 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  }

  btnSaveRows?.addEventListener("click", saveRows);

  /* =======================================================
     📌 4. 데이터 삭제 (ajax_delete)
  ======================================================= */
  function attachDeleteHandlers() {
    document.querySelectorAll(".btnDeleteRow").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("이 항목을 삭제하시겠습니까?")) return;
        const id = btn.dataset.id;

        showLoading("삭제 중...");

        try {
          const res = await fetch(dataDeleteUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() || document.querySelector('[name=csrfmiddlewaretoken]')?.value || "" },
            body: JSON.stringify({ id }),
          });
          const data = await res.json();
          if (data.status === "success") {
            alertBox("삭제 완료");
            fetchData();
          } else {
            alertBox(data.message);
          }
        } catch (err) {
          console.error(err);
          alertBox("삭제 중 오류 발생");
        } finally {
          hideLoading();
        }
      });
    });
  }

  /* =======================================================
     📌 5. 입력기한 설정 (ajax_set_deadline)
  ======================================================= */
  btnSetDeadline?.addEventListener("click", async () => {
    const branch = branchSelect?.value || "";
    const day = deadlineSelect?.value || "";
    const month = `${yearSelect.value}-${monthSelect.value.padStart ? monthSelect.value.padStart(2, "0") : ("0" + monthSelect.value).slice(-2)}`;

    if (!branch && !day) return alertBox("부서와 기한을 선택해주세요.");
    if (!branch) return alertBox("부서를 선택해주세요.");
    if (!day) return alertBox("기한을 선택해주세요.");

    showLoading("기한 설정 중...");

    try {
      const res = await fetch(setDeadlineUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() || document.querySelector('[name=csrfmiddlewaretoken]')?.value || "" },
        body: JSON.stringify({ branch, deadline_day: day, month }),
      });
      const data = await res.json();
      alertBox(data.message || "기한 설정 완료");
    } catch (err) {
      console.error(err);
      alertBox("기한 설정 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  });

  /* =======================================================
     📌 6. CSRF Token Helper
  ======================================================= */
  function getCSRFToken() {
    const name = "csrftoken";
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith(name + "="));
    return cookieValue ? cookieValue.split("=")[1] : "";
  }

  /* =======================================================
     📌 7. DataTables 초기화
  ======================================================= */
  if (window.jQuery && $.fn.DataTable) {
    $(mainTable).DataTable({
      language: { search: "검색 :", lengthMenu: "표시 _MENU_ 개" },
      order: [],
    });
  }

  /* =======================================================
     📌 8. 입력 가능 여부 제어 + 기본 기한(10일) 적용
  ======================================================= */
  const today = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const selectedYear = parseInt(yearSelect.value);
  const selectedMonth = parseInt(monthSelect.value);
  const deadlineDay = window.ManageStructureBoot.deadlineDay;

  // ✅ 기한 없으면 기본 10일 적용
  const effectiveDeadline = deadlineDay || 10;

  // ✅ 안내문 표시
  if (!deadlineDay) {
    console.warn("⚠️ 기한이 설정되지 않아 기본 10일로 적용됩니다.");
    const hintBox = document.getElementById("periodHints");
    if (hintBox) {
      const note = document.createElement("div");
      note.className = "text-warning small mt-1";
      note.textContent = "⚠️ 기한이 설정되지 않아 기본 10일로 적용됩니다.";
      hintBox.appendChild(note);
    }
  }

  // ✅ 입력 가능 여부 판단
  function checkInputAvailability() {
    inputSection.classList.remove("disabled-mode");
    inputSection.querySelectorAll("input, select, button").forEach(el => el.disabled = false);

    const isPastMonth =
      selectedYear < currentYear ||
      (selectedYear === currentYear && selectedMonth < currentMonth);

    const isDeadlineOver =
      selectedYear === currentYear &&
      selectedMonth === currentMonth &&
      today.getDate() > effectiveDeadline;

    if (isPastMonth || isDeadlineOver) {
      inputSection.classList.add("disabled-mode");
      inputSection.querySelectorAll("input, select, button").forEach(el => el.disabled = true);
    }
  }

  // 초기 및 변경 시 체크
  checkInputAvailability();
  yearSelect.addEventListener("change", checkInputAvailability);
  monthSelect.addEventListener("change", checkInputAvailability);

  console.log("✅ Manage Structure JS Loaded with deadline rules");
});
