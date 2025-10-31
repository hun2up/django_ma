import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox } from "./utils.js";
import { fetchData } from "./fetch.js";

/* =======================================================
   📘 입력 행 관련 로직
   ======================================================= */
export function initInputRowEvents() {
  // ✅ 추가 버튼
  els.btnAddRow?.addEventListener("click", () => {
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length >= 10) {
      alertBox("대상자는 한 번에 10명까지 입력 가능합니다.");
      return;
    }
    const newRow = rows[0].cloneNode(true);
    newRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
    });
    fillRequesterInfo(newRow);
    tbody.appendChild(newRow);
  });

  // ✅ 초기화 버튼
  els.btnResetRows?.addEventListener("click", () => {
    if (!confirm("입력 내용을 모두 초기화하시겠습니까?")) return;
    resetInputSection();
  });

  // ✅ 삭제 버튼 (동적 위임)
  document.addEventListener("click", (e) => {
    if (!e.target.classList.contains("btnRemoveRow")) return;
    const tbody = els.inputTable.querySelector("tbody");
    const rows = tbody.querySelectorAll(".input-row");
    if (rows.length <= 1) {
      alertBox("행이 하나뿐이라 삭제할 수 없습니다.");
      return;
    }
    e.target.closest(".input-row").remove();
  });

  // ✅ 저장 버튼
  els.btnSaveRows?.addEventListener("click", async () => {
    await saveRowsToServer();
  });

  // ✅ 페이지 최초 로드시 요청자 정보 입력
  const firstRow = els.inputTable.querySelector(".input-row");
  if (firstRow) fillRequesterInfo(firstRow);
}

/* =======================================================
   ✅ 요청자 정보 자동입력
   ======================================================= */
function fillRequesterInfo(row) {
  const user = window.currentUser || {};
  row.querySelector('input[name="rq_name"]').value = user.name || "";
  row.querySelector('input[name="rq_id"]').value = user.id || "";
  row.querySelector('input[name="rq_branch"]').value = user.branch || "";
}

/* =======================================================
   ✅ 전체 입력 초기화
   ======================================================= */
export function resetInputSection() {
  const tbody = els.inputTable.querySelector("tbody");
  tbody.querySelectorAll(".input-row").forEach((r, i) => {
    if (i > 0) r.remove();
  });
  const firstRow = tbody.querySelector(".input-row");
  if (firstRow) {
    firstRow.querySelectorAll("input").forEach((el) => {
      if (el.type === "checkbox") el.checked = false;
      else el.value = "";
    });
    fillRequesterInfo(firstRow);
  }
}

/* =======================================================
   ✅ 저장 버튼 클릭 → 서버로 전송 + 메인시트 갱신
   ======================================================= */
async function saveRowsToServer() {
  const tbody = els.inputTable.querySelector("tbody");
  const rows = tbody.querySelectorAll(".input-row");
  const validRows = [];

  rows.forEach((row) => {
    const tg_id = row.querySelector('input[name="tg_id"]').value.trim();
    const tg_name = row.querySelector('input[name="tg_name"]').value.trim();
    if (!tg_id || !tg_name) return; // ❌ 대상자 누락 시 제외

    validRows.push({
      target_id: tg_id,
      target_name: tg_name,
      tg_branch: row.querySelector('input[name="tg_branch"]').value.trim(),
      tg_rank: row.querySelector('input[name="tg_rank"]').value.trim(),
      chg_branch: row.querySelector('input[name="chg_branch"]').value.trim(),
      chg_rank: row.querySelector('input[name="chg_rank"]').value.trim(),
      memo: row.querySelector('input[name="memo"]').value.trim(),
      or_flag: row.querySelector('input[name="or_flag"]').checked,
    });
  });

  if (validRows.length === 0) {
    alertBox("대상자 정보가 입력된 행이 없습니다.");
    return;
  }

  const user = window.currentUser || {};
  const boot = window.ManageStructureBoot || {};
  const year = document.getElementById("yearSelect")?.value;
  const month = document.getElementById("monthSelect")?.value;
  const ym = `${year}-${String(month).padStart(2, "0")}`;

  const branch =
    user.grade === "superuser"
      ? document.getElementById("branchSelect")?.value?.trim() || "-"
      : user.branch || "-";

  const payload = {
    month: ym,
    rows: validRows,
    part: user.part || "-",
    branch: branch,
  };

  console.log("💾 서버로 저장 요청:", payload);

  showLoading("저장 중입니다...");

  try {
    const res = await fetch(boot.dataSaveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.csrfToken,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    hideLoading();

    if (data.status === "success") {
      alertBox(data.message || "저장 완료!");

      // ✅ 저장 후 입력초기화
      resetInputSection();

      // ✅ 저장 후 메인시트 즉시 갱신
      const meta = {
        grade: user.grade,
        level: user.level,
        team_a: user.team_a,
        team_b: user.team_b,
        team_c: user.team_c,
      };
      await fetchData(ym, branch, meta);
    } else {
      alertBox(data.message || "저장 중 오류가 발생했습니다.");
    }
  } catch (err) {
    console.error("❌ 저장 실패:", err);
    hideLoading();
    alertBox("저장 중 오류가 발생했습니다.");
  }
}
