// django_ma/static/js/partner/manage_structure/save.js
// =========================================================
// ✅ Structure - Save (Final Refactor)
// - 입력행 수집/검증
// - 저장 성공 시: ✅ 필터 저장(sessionStorage) → ✅ page reload
// - (메인시트가 간헐적으로 빈 화면 되는 DT 타이밍 이슈를 reload로 확실히 해결)
// =========================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken, selectedYM } from "./utils.js";
import { resetInputSection } from "./input_rows.js";

function toStr(v) {
  return String(v ?? "").trim();
}

function getSaveUrl() {
  // 템플릿: data-data-save-url => dataset.dataSaveUrl
  return toStr(els.root?.dataset?.dataSaveUrl || els.root?.dataset?.dataDataSaveUrl || "");
}

function getBranchForSave() {
  // superuser면 선택값 우선(없으면 빈값)
  const grade = toStr(els.root?.dataset?.userGrade || window.currentUser?.grade || "");
  if (grade === "superuser") {
    return toStr(els.branch?.value || els.branchSelect?.value || "");
  }
  return toStr(window.currentUser?.branch || els.root?.dataset?.defaultBranch || "");
}

function stashFiltersForReloadFallback() {
  // index.js가 window.__manageStructure로 주입해두면 그걸 사용
  try {
    const fn = window.__manageStructure?.stashFiltersForReload;
    if (typeof fn === "function") {
      fn();
      return;
    }
  } catch (_) {}

  // (방어) 혹시 index.js 로드 순서 문제면 여기서 직접 저장
  try {
    const y = toStr(document.getElementById("yearSelect")?.value);
    const m = toStr(document.getElementById("monthSelect")?.value);

    const channel = toStr(document.getElementById("channelSelect")?.value);
    const part = toStr(document.getElementById("partSelect")?.value);
    const branch = toStr(document.getElementById("branchSelect")?.value);

    sessionStorage.setItem(
      "__manage_structure_filters__",
      JSON.stringify({ y, m, channel, part, branch })
    );
  } catch (e) {
    console.warn("stashFiltersForReloadFallback failed:", e);
  }
}

/**
 * ✅ 편제변경 저장 (안전형 + 저장 성공 시 reload)
 */
export async function saveRows() {
  if (!els.inputTable) return;

  const rows = Array.from(els.inputTable.querySelectorAll("tbody tr.input-row"));
  const payload = [];

  // 🔹 데이터 수집 및 검증
  for (const row of rows) {
    const rq_id = toStr(row.querySelector("[name='rq_id']")?.value);
    const tg_id = toStr(row.querySelector("[name='tg_id']")?.value);

    if (!tg_id) {
      alertBox("대상자를 선택해주세요.");
      return;
    }

    payload.push({
      requester_id: rq_id,
      target_id: tg_id,
      tg_rank: toStr(row.querySelector("[name='tg_rank']")?.value),
      chg_branch: toStr(row.querySelector("[name='chg_branch']")?.value),
      or_flag: !!row.querySelector("[name='or_flag']")?.checked,
      chg_rank: toStr(row.querySelector("[name='chg_rank']")?.value),
      memo: toStr(row.querySelector("[name='memo']")?.value),
    });
  }

  if (!payload.length) {
    alertBox("저장할 데이터가 없습니다.");
    return;
  }

  const saveUrl = getSaveUrl();
  if (!saveUrl) {
    alertBox("저장 URL이 없습니다. (data-data-save-url / dataset.dataSaveUrl 확인)");
    return;
  }

  const ym = selectedYM(els.year, els.month);
  const part = toStr(els.part?.value || window.currentUser?.part || "");
  const branch = getBranchForSave();

  showLoading("저장 중...");

  try {
    const res = await fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        rows: payload,
        month: ym,
        part,
        branch,
      }),
    });

    const text = await res.text().catch(() => "");
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

      // ✅ 저장 성공 → 필터 저장 후 새로고침
      stashFiltersForReloadFallback();
      window.location.reload();
      return;
    }

    alertBox(result.message || "저장 중 오류가 발생했습니다.");
  } catch (err) {
    console.error("❌ saveRows error:", err);
    alertBox(err?.message || "저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
