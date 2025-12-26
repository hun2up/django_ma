// django_ma/static/js/partner/manage_structure/save.js

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken, selectedYM } from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

/**
 * ✅ 편제변경 저장 (안전형)
 */
export async function saveRows() {
  const rows = Array.from(els.inputTable.querySelectorAll("tbody tr.input-row"));
  const payload = [];

  // 🔹 데이터 수집 및 검증
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
      tg_rank: row.querySelector("[name='tg_rank']")?.value.trim() || "",
      chg_branch: row.querySelector("[name='chg_branch']")?.value.trim() || "",
      or_flag: row.querySelector("[name='or_flag']")?.checked || false,
      chg_rank: row.querySelector("[name='chg_rank']")?.value.trim() || "",
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
        part: els.branch?.value || window.currentUser?.part || "",
        branch: els.branch?.value || window.currentUser?.branch || "",
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
      const count = result.saved_count ?? payload.length;
      alertBox(`✅ ${count}건 저장 완료`);

      // 🔹 입력 폼 리셋
      resetInputSection();

      // 🔹 재조회 (안전 실행)
      try {
        const ym = `${els.year.value}-${els.month.value}`;
        const branch = els.branch?.value || window.currentUser?.branch || "";
        await fetchData(ym, branch);
      } catch (reErr) {
        console.warn("⚠️ 저장 후 재조회 중 오류:", reErr);
        alertBox("저장은 완료되었지만, 테이블 새로고침 중 오류가 발생했습니다.");
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
