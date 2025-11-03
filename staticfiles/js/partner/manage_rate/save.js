// django_ma/static/js/parnter/manage_rate/save.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken, selectedYM } from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

/**
 * ✅ 요율변경 요청 저장 (요청자 branch 포함)
 */
export async function saveRows() {
  const rows = Array.from(els.inputTable.querySelectorAll("tbody tr.input-row"));
  const payload = [];

  for (const row of rows) {
    const rq_id = row.querySelector("[name='rq_id']")?.value.trim() || "";
    const tg_id = row.querySelector("[name='tg_id']")?.value.trim() || "";

    if (!tg_id) {
      alertBox("대상자를 선택해주세요.");
      return;
    }

    payload.push({
      requester_id: rq_id,
      target_id: tg_id,
      rq_branch: window.currentUser?.branch || "",
      after_ftable: row.querySelector("[name='after_ftable']")?.value.trim() || "",
      after_frate: row.querySelector("[name='after_frate']")?.value.trim() || "",
      after_ltable: row.querySelector("[name='after_ltable']")?.value.trim() || "",
      after_lrate: row.querySelector("[name='after_lrate']")?.value.trim() || "",
      memo: row.querySelector("[name='memo']")?.value.trim() || "",
    });
  }

  if (!payload.length) {
    alertBox("저장할 데이터가 없습니다.");
    return;
  }

  showLoading("저장 중...");

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
        branch: window.currentUser?.branch || "",
      }),
    });

    const text = await res.text();
    console.log("📦 [saveRows] Raw Response:", text);
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    let result = {};
    try {
      result = JSON.parse(text);
    } catch {
      throw new Error("서버 응답 파싱 실패");
    }

    if (result.status === "success") {
      alertBox(`✅ ${result.saved_count ?? payload.length}건 저장 완료`);
      resetInputSection();

      try {
        const ym = `${els.yearSelect?.value || new Date().getFullYear()}-${(els.monthSelect?.value || new Date().getMonth() + 1)
          .toString()
          .padStart(2, "0")}`;
        const branch = window.currentUser?.branch || "";
        await fetchData({ ym, branch });
      } catch (reErr) {
        console.warn("⚠️ 저장 후 재조회 중 오류:", reErr);
      }
    } else {
      alertBox(result.message || "저장 중 오류가 발생했습니다.");
    }
  } catch (err) {
    console.error("❌ saveRows error:", err);
    alertBox("저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
