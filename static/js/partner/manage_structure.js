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

  /* ------------------------------
     📌 요청자 소속 표시 규칙
  ------------------------------ */
  function formatRequesterBranch(user) {
    const grade = user.grade || "";
    const level = (user.level || "").toUpperCase();
    const branch = user.branch || "";
    const teamA = user.team_a || "";
    const teamB = user.team_b || "";
    const teamC = user.team_c || "";
    const part = user.part || "";

    if (grade === "superuser") return part || "-";
    if (grade === "main_admin") return branch || "-";
    if (grade === "sub_admin") {
      if (level === "A") return [teamA].filter(Boolean).join(" + ");
      if (level === "B") return [teamA, teamB].filter(Boolean).join(" + ");
      if (level === "C") return [teamA, teamB, teamC].filter(Boolean).join(" + ");
    }
    return branch || part || "-";
  }

  window.formatRequesterBranch = formatRequesterBranch;

  /* ------------------------------
     📌 대상자 소속 표시 규칙 (기존 유지)
  ------------------------------ */
  function formatTargetBranch(user) {
    const teamA = user.team_a || "";
    const teamB = user.team_b || "";
    const teamC = user.team_c || "";
    if (teamC) return teamC;
    if (teamB) return [teamB, teamC].filter(Boolean).join(" + ");
    if (teamA) return [teamA, teamB, teamC].filter(Boolean).join(" + ");
    return user.branch || "-";
  }

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
    📌 2. 데이터 조회 (개선버전)
  ======================================================= */
  async function fetchData(ym = null, branchValue = null) {
    const y = ym ? ym.split("-")[0] : els.year.value;
    const m = ym ? ym.split("-")[1] : els.month.value;
    const b = branchValue !== null ? branchValue : els.branch?.value || "";
    const ymValue = `${y}-${pad2(m)}`;

    showLoading("데이터 불러오는 중...");

    if (userGrade === "superuser" && !b) {
      alertBox("부서를 선택해주세요.");
      hideLoading();
      return;
    }

    try {
      // ✅ 실제 fetch 호출
      const res = await fetch(`${dataFetchUrl}?month=${ymValue}&branch=${b}`);
      if (!res.ok) throw new Error("조회 실패");

      const data = await res.json();
      console.log("✅ fetchData 응답:", data);

      renderMainTable(data.rows || []);
    } catch (err) {
      console.error("❌ fetchData 오류:", err);
      alertBox("데이터를 불러오지 못했습니다.");
    } finally {
      hideLoading();
    }
  }

  /* ✅ 테이블 렌더링 */
  function renderMainTable(rows) {
    const canEditProcessDate = ["superuser", "main_admin"].includes(userGrade);
    const canDelete = ["superuser", "main_admin"].includes(userGrade);
    const updateUrl = root.dataset.updateProcessDateUrl;
    const tbody = els.mainTable.querySelector("tbody");
    tbody.innerHTML = "";

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="17" class="text-center text-muted py-3">데이터가 없습니다.</td></tr>`;
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
          <td class="text-blue">${r.target_name || "-"}</td>
          <td>${r.target_id || "-"}</td>
          <td>${r.target_branch || "-"}</td>
          <td class="text-blue">${r.chg_branch || "-"}</td>          
          <td>${r.rank || "-"}</td>
          <td class="text-blue">${r.chg_rank || "-"}</td>
          <td class="text-center">${r.or_flag ? "✅" : "❌"}</td>
          <td>${r.memo || "-"}</td>
          <td>${r.request_date || "-"}</td>
          <td class="text-blue">
            ${
              canEditProcessDate
                ? `<input type="date" class="form-control form-control-sm process-date-input" 
                          value="${r.process_date || ""}" data-id="${r.id}">`
                : `${r.process_date || "-"}`
            }
          </td>
          <td>
            ${
              canDelete
                ? `<button class="btn btn-outline-danger btn-sm btnDeleteRow" data-id="${r.id}">삭제</button>`
                : `<button class="btn btn-outline-secondary btn-sm" disabled>삭제</button>`
            }
          </td>
        </tr>`
      );
    });
    attachDeleteHandlers();
    
    // ✅ 처리일자 변경 이벤트
    if (canEditProcessDate) {
      tbody.querySelectorAll(".process-date-input").forEach((input) => {
        input.addEventListener("change", async (e) => {
          const id = e.target.dataset.id;
          const newDate = e.target.value;
          if (!newDate) return alert("날짜를 선택하세요.");

          showLoading("처리일자 변경 중...");
          try {
            const res = await fetch(updateUrl, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
              },
              body: JSON.stringify({ id, process_date: newDate }),
            });
            const data = await res.json();
            alert(data.message || "변경 완료");
          } catch (err) {
            console.error(err);
            alert("처리일자 변경 중 오류가 발생했습니다.");
          } finally {
            hideLoading();
          }
        });
      });
    }
  }

  /* ✅ 검색 버튼 클릭 시 fetchData 실행 */
  els.btnSearch?.addEventListener("click", () => fetchData());


  /* =======================================================
    📌 3. 데이터 저장
  ======================================================= */
  async function saveRows() {
    const rows = Array.from(document.querySelectorAll("#inputTable tbody tr"));
    const payload = [];

    for (const row of rows) {
      const rq_id = row.querySelector("[name='rq_id']").value.trim();
      const tg_id = row.querySelector("[name='tg_id']").value.trim();

      // ✅ 1️⃣ 대상자 미선택 검증
      if (!tg_id) {
        alertBox("대상자를 선택해주세요.");
        return;
      }

      const data = {
        requester_id: rq_id,
        target_id: tg_id,
        chg_branch: row.querySelector("[name='chg_branch']").value.trim(),
        or_flag: row.querySelector("[name='or_flag']").checked,
        chg_rank: row.querySelector("[name='chg_rank']").value.trim(),
        memo: row.querySelector("[name='memo']").value.trim(),
      };
      payload.push(data);
    }

    if (!payload.length) {
      alertBox("저장할 데이터가 없습니다.");
      return;
    }

    showLoading("저장 중...");

    try {
      const res = await fetch(dataSaveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({
          rows: payload,
          month: selectedYM(),
          part: els.branch?.value || window.currentUser?.part || "",
          branch: els.branch?.value || window.currentUser?.branch || "",
        }),
      });

      if (!res.ok) throw new Error("저장 실패");

      const result = await res.json();
      if (result.status === "success") {
        alertBox(`${result.saved_count}건 저장 완료`);
        resetInputSection(); 

        // ✅ 2️⃣ 저장 후 다시 조회 (branch 값 유지)
        const year = els.year.value;
        const month = els.month.value;
        const branch = els.branch?.value || "";
        await fetchData(`${year}-${month}`, branch);

      } else {
        alertBox("저장 중 오류가 발생했습니다.");
      }
    } catch (err) {
      console.error("❌ saveRows 오류:", err);
      alertBox("저장 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
    }
  }

  /* =======================================================
    📌 이벤트 연결
  ======================================================= */
  els.btnSaveRows?.addEventListener("click", saveRows);


  /* =======================================================
    📌 입력영역 초기화 함수
  ======================================================= */
  function resetInputSection() {
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");

    // 첫 행만 남기고 나머지는 삭제
    rows.forEach((r, idx) => {
      if (idx > 0) r.remove();
    });

    // 첫 행 input 값 초기화
    const firstRow = tbody.querySelector(".input-row");
    if (firstRow) {
      firstRow.querySelectorAll("input").forEach((el) => {
        if (el.type === "checkbox") el.checked = false;
        else el.value = "";
      });
    }
  }


  /* =======================================================
    📌 대상자 입력행 제어 (추가 / 초기화)
  ======================================================= */

  // ✅ 행 추가
  els.btnAddRow?.addEventListener("click", () => {
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");

    // 최대 10개 제한
    if (rows.length >= 10) {
      alertBox("대상자는 한 번에 10명까지 입력 가능합니다.");
      return;
    }

    // 첫 번째 행 복제
    const newRow = rows[0].cloneNode(true);

    // 복제한 행의 input 초기화
    newRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") {
        el.checked = false;
      } else {
        el.value = "";
      }
    });

    tbody.appendChild(newRow);
  });

  // ✅ 초기화 버튼
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");

    // 첫 행만 남기고 모두 삭제
    rows.forEach((r, idx) => {
      if (idx > 0) r.remove();
    });

    // 첫 행 input 초기화
    const firstRow = tbody.querySelector(".input-row");
    if (firstRow) {
      firstRow.querySelectorAll("input").forEach((el) => {
        if (el.type === "checkbox") el.checked = false;
        else el.value = "";
      });
    }
  });


  /* =======================================================
    📌 입력행 삭제 기능
    ======================================================= */
  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("btnRemoveRow")) return;

    const tbody = document.querySelector("#inputTable tbody");
    const rows = tbody.querySelectorAll(".input-row");

    // ✅ 행이 하나밖에 없으면 삭제 금지
    if (rows.length <= 1) {
      alert("행이 하나뿐이라 삭제할 수 없습니다.");
      return;
    }

    // ✅ 클릭된 버튼이 속한 행 삭제
    e.target.closest(".input-row").remove();
  });


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
            credentials: "include",
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

  // ✅ main_admin / sub_admin 모두 자동조회
  if (["main_admin", "sub_admin"].includes(userGrade)) {
    const year = els.year.value;
    const month = els.month.value;
    const branch = els.branch?.value || "";
    setTimeout(() => fetchData(`${year}-${month}`, branch), 300);
  }

  // ✅ 항상 대상자 입력 섹션 표시 (디버그용)
  els.inputSection.removeAttribute("hidden");

  /* =======================================================
     📌 공통 모달에서 선택된 사용자 이벤트 수신
  ======================================================= */
  document.addEventListener("userSelected", (e) => {
    const { id, name, branch, part, rank, regist } = e.detail;
    const targetRow = document.querySelector("#inputTable tbody tr:last-child");
    if (!targetRow) return alert("입력 행이 존재하지 않습니다.");

    // 대상자 정보 채우기
    targetRow.querySelector("input[name='tg_id']").value = id;
    targetRow.querySelector("input[name='tg_name']").value = name;
    targetRow.querySelector("input[name='tg_branch']").value = `${part} ${branch}`;
    targetRow.querySelector("input[name='tg_rank']").value = rank || "";
    if (targetRow.querySelector("input[name='tg_regist']"))
      targetRow.querySelector("input[name='tg_regist']").value = regist || "";

    // 요청자 정보도 자동 입력
    const rqBranch = formatRequesterBranch(window.currentUser);
    targetRow.querySelector("input[name='rq_name']").value = window.currentUser?.name || "";
    targetRow.querySelector("input[name='rq_id']").value = window.currentUser?.id || "";
    targetRow.querySelector("input[name='rq_branch']").value = rqBranch;
  });

  /* =======================================================
    📌 대상자 검색 모달 — 기본 submit 차단 + 검색 로직
  ======================================================= */
  const searchForm = document.getElementById("searchUserForm");
  if (searchForm) {
    searchForm.addEventListener("submit", async (e) => {
      e.preventDefault(); // ✅ 폼 제출 기본 동작 차단 (모달 닫힘 방지)

      const keyword = document.getElementById("searchKeyword").value.trim();
      if (!keyword) return alert("검색어를 입력하세요.");

      // ✅ Ajax 요청 (기존 /board/search-user/ 재사용)
      const url = root.dataset.searchUserUrl || "/board/search-user/";
      try {
        const res = await fetch(`${url}?q=${encodeURIComponent(keyword)}`);
        if (!res.ok) throw new Error("검색 실패");
        const data = await res.json();

        // ✅ 검색 결과 표시
        const results = document.getElementById("searchResults");
        if (!data.results?.length) {
          results.innerHTML = `<div class="text-muted small mt-2">검색 결과가 없습니다.</div>`;
        } else {
          results.innerHTML = data.results
            .map(
              (u) => `
                <div class="border rounded p-2 mb-1 d-flex justify-content-between align-items-center">
                  <div>
                    <strong>${u.name}</strong> (${u.id})
                    ${u.regist ? ` <span class="text-muted">(${u.regist})</span>` : ""}<br>
                    <small class="text-muted">
                      ${u.part || ""}${u.branch ? " " + u.branch : ""}
                    </small>
                  </div>
                  <button type="button" class="btn btn-sm btn-outline-primary selectUserBtn"
                          data-id="${u.id}" 
                          data-name="${u.name}" 
                          data-branch="${u.branch || ""}"
                          data-part="${u.part || ""}"
                          data-rank="${u.rank || ""}"
                          data-regist="${u.regist || ""}">
                    선택
                  </button>
                </div>`
            )
            .join("");
        }
      } catch (err) {
        console.error(err);
        alert("검색 중 오류가 발생했습니다.");
      }
    });
  }

  /* =======================================================
    📌 검색결과 선택 버튼 처리
  ======================================================= */
  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("selectUserBtn")) return;

    const btn = e.target;
    const userId = btn.dataset.id;
    const userName = btn.dataset.name;
    const userBranch = btn.dataset.branch || "";
    const userPart = btn.dataset.part || "";
    const userRank = btn.dataset.rank || "";
    const userRegist = btn.dataset.regist || "";

    const targetRow = document.querySelector("#inputTable tbody tr:last-child");
    if (!targetRow) return alert("입력 행이 존재하지 않습니다.");

    targetRow.querySelector("input[name='tg_id']").value = userId;
    targetRow.querySelector("input[name='tg_name']").value = userName;
    targetRow.querySelector("input[name='tg_branch']").value = `${userPart} ${userBranch}`;
    targetRow.querySelector("input[name='tg_rank']").value = userRank;
    if (targetRow.querySelector("input[name='tg_regist']"))
      targetRow.querySelector("input[name='tg_regist']").value = userRegist;

    // 요청자 정보 자동입력
    targetRow.querySelector("input[name='rq_name']").value = window.currentUser?.name || "";
    targetRow.querySelector("input[name='rq_id']").value = window.currentUser?.id || "";
    targetRow.querySelector("input[name='rq_branch']").value = window.currentUser?.branch || "";

    // 모달 닫기
    const modal = bootstrap.Modal.getInstance(document.getElementById("searchUserModal"));
    if (modal) modal.hide();

    document.getElementById("searchResults").innerHTML = "";
    document.getElementById("searchKeyword").value = "";
  });
});
