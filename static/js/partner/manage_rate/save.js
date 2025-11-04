// ======================================================
// 📘 요율변경 요청 페이지 - 저장 로직 (v5.2)
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken, selectedYM } from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

/* =======================================================
   ✅ 저장 버튼 클릭 시 실행
   ======================================================= */
export async function saveRows() {
  const rows = Array.from(els.inputTable.querySelectorAll("tbody tr.input-row"));
  const payload = [];

  for (const row of rows) {
    const rq_id = row.querySelector('[name="rq_id"]')?.value.trim();
    const tg_id = row.querySelector('[name="tg_id"]')?.value.trim();

    if (!tg_id) {
      alertBox("대상자를 선택해주세요.");
      return;
    }

    payload.push({
      requester_id: rq_id || window.currentUser?.id || "",
      target_id: tg_id,
      before_ftable: row.querySelector('[name="before_ftable"]')?.value || "",
      before_frate: row.querySelector('[name="before_frate"]')?.value || "",
      before_ltable: row.querySelector('[name="before_ltable"]')?.value || "",
      before_lrate: row.querySelector('[name="before_lrate"]')?.value || "",
      after_ftable:
        row.querySelector('select[name="after_ftable"]')?.value ||
        row.querySelector('input[name="after_ftable"]')?.value ||
        "",
      after_frate: row.querySelector('[name="after_frate"]')?.value || "",
      after_ltable:
        row.querySelector('select[name="after_ltable"]')?.value ||
        row.querySelector('input[name="after_ltable"]')?.value ||
        "",
      after_lrate: row.querySelector('[name="after_lrate"]')?.value || "",
      memo: row.querySelector('[name="memo"]')?.value || "",
    });
  }

  if (!payload.length) {
    alertBox("저장할 데이터가 없습니다.");
    return;
  }

  showLoading("저장 중...");
  console.log("💾 저장 payload:", payload);

  try {
    const res = await fetch(els.root.dataset.dataSaveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        rows: payload,
        month: selectedYM(els.year, els.month),
        part: window.currentUser?.part || "",
        branch: window.currentUser?.branch || "", // ← 단순 조회 참고용
      }),
    });

    const data = await res.json();

    if (data.status === "success") {
      alertBox(`✅ ${data.saved_count || payload.length}건 저장 완료`);
      resetInputSection();
      await fetchData(selectedYM(els.year, els.month), window.currentUser?.branch || "");
    } else {
      throw new Error(data.message || "저장 실패");
    }
  } catch (err) {
    console.error("❌ saveRows 오류:", err);
    alertBox("저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
