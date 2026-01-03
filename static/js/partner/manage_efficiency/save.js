// django_ma/static/js/partner/manage_efficiency/save.js
//
// ✅ Refactor (2026-01-02)
// - manage_calculate.html 입력폼 기준(category/amount/ded/pay/content) 수집
// - ✅ 확인서 업로드 필수: confirmAttachmentId 없으면 저장 차단
// - JSON 저장 + raw response 로그 유지
// - 저장 후 resetInputSection() + fetchData(ym,branch) 재조회
// - superuser/main/sub branch 처리 규칙 유지

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken, selectedYM, pad2 } from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

function str(v) {
  return String(v ?? "").trim();
}

/* =========================================================
   Confirm(확인서) helpers
========================================================= */
function getConfirmAttachmentId() {
  return str(document.getElementById("confirmAttachmentId")?.value || "");
}
function mustHaveConfirmOrAlert() {
  const attId = getConfirmAttachmentId();
  if (!attId) {
    alertBox("※ 반드시 확인서를 첨부해야 내용 저장이 가능합니다.");
    return null;
  }
  return attId;
}

function getBranchForSave() {
  // superuser는 els.branch(=branchSelect) 값 사용, 없으면 빈값
  // main/sub는 currentUser.branch를 우선
  const dsBranch = str(els.root?.dataset?.branch || "");
  return str(els.branch?.value) || str(window.currentUser?.branch) || dsBranch || "";
}

function getPartForSave() {
  // 효율 페이지도 build_manage_context에서 currentUser.part 내려줌
  return str(window.currentUser?.part) || "";
}

function normalizeAmount(raw) {
  // "1,000,000" 같은 입력을 안전하게 숫자만 추출
  const digits = String(raw ?? "").replace(/[^\d]/g, "");
  const n = parseInt(digits || "0", 10);
  return Number.isFinite(n) ? n : 0;
}

/**
 * ✅ 지점효율 저장 (확인서 필수)
 */
export async function saveRows() {
  const table = els.inputTable || document.getElementById("inputTable");
  if (!table) {
    alertBox("입력 테이블을 찾을 수 없습니다.");
    return;
  }

  // ✅ 확인서 필수
  const confirmAttachmentId = mustHaveConfirmOrAlert();
  if (!confirmAttachmentId) return;

  const rows = Array.from(table.querySelectorAll("tbody tr.input-row"));
  const payloadRows = [];

  for (const row of rows) {
    const category = str(row.querySelector("[name='category']")?.value || "");
    const amountRaw = row.querySelector("[name='amount']")?.value ?? "";
    const amount = normalizeAmount(amountRaw);

    const content = str(row.querySelector("[name='content']")?.value || "");

    // 공제자/지급자(선택)
    const ded_name = str(row.querySelector("[name='ded_name']")?.value || "");
    const ded_id = str(row.querySelector("[name='ded_id']")?.value || "");
    const pay_name = str(row.querySelector("[name='pay_name']")?.value || "");
    const pay_id = str(row.querySelector("[name='pay_id']")?.value || "");

    // ✅ 필수 검증 (템플릿에 * 표시된 것들)
    if (!category || amount <= 0 || !content) {
      alertBox("구분/금액/내용은 필수입니다. 입력값을 확인해주세요.");
      return;
    }

    payloadRows.push({
      category,
      amount,
      ded_name,
      ded_id,
      pay_name,
      pay_id,
      content,
    });
  }

  if (!payloadRows.length) {
    alertBox("저장할 데이터가 없습니다.");
    return;
  }

  // ✅ 월/지점
  const ym = selectedYM(els.year, els.month); // "YYYY-MM"
  const branch = getBranchForSave();
  const part = getPartForSave();

  if (!ym) {
    alertBox("연도/월도를 확인해주세요.");
    return;
  }
  if (!branch && str(window.currentUser?.grade) === "superuser") {
    alertBox("지점을 먼저 선택하세요.");
    return;
  }

  showLoading("저장 중...");

  try {
    const url = els.root?.dataset?.dataSaveUrl;
    if (!url) throw new Error("dataSaveUrl이 없습니다.");

    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        rows: payloadRows,
        month: ym,
        part,
        branch,
        confirm_attachment_id: els.root?.dataset?.confirmAttachmentId || "",

      }),
    });

    const text = await res.text();
    console.log("📦 [efficiency/saveRows] Raw Response:", text);

    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    let result = {};
    try {
      result = JSON.parse(text);
    } catch {
      throw new Error("서버 응답 파싱 실패");
    }

    if (result.status === "success") {
      const count = result.saved_count ?? payloadRows.length;
      alertBox(`✅ ${count}건 저장 완료`);

      // ✅ 입력 폼 리셋(+ 확인서 상태도 초기화 권장)
      try {
        resetInputSection();
      } catch (e) {
        console.warn("⚠️ resetInputSection 실패(무시):", e);
      }

      // 확인서 UI 초기화 (첨부는 저장 1회 단위로 강제)
      const attEl = document.getElementById("confirmAttachmentId");
      const nameEl = document.getElementById("confirmFileName");
      const fileEl = document.getElementById("confirmFileInput");
      if (attEl) attEl.value = "";
      if (nameEl) nameEl.value = "";
      if (fileEl) fileEl.value = "";

      // ✅ 재조회
      try {
        await fetchData(ym, branch);
      } catch (reErr) {
        console.warn("⚠️ 저장 후 재조회 오류:", reErr);
        alertBox("저장은 완료되었지만, 테이블 새로고침 중 오류가 발생했습니다.");
      }
    } else {
      alertBox(result.message || "저장 중 오류가 발생했습니다.");
    }
  } catch (err) {
    console.error("❌ efficiency saveRows error:", err);
    alertBox("저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
