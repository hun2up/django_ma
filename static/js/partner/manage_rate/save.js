// django_ma/static/js/partner/manage_rate/save.js
// ======================================================
// 📘 요율변경 요청 페이지 - 저장 로직 (final refactor)
//  - input/select 혼용 지원 (after_ftable/after_ltable)
//  - 필수값 검증, 중복 대상자 검증
//  - dataset 기반 URL 사용 (하드코딩 제거)
//  - 저장 후 reset + 재조회(fetchData)
// ======================================================

import { els } from "./dom_refs.js";
import {
  showLoading,
  hideLoading,
  alertBox,
  getCSRFToken,
  selectedYM,
} from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

/* ==========================
   ✅ helpers
========================== */
function ds(key, fallback = "") {
  return (els.root?.dataset?.[key] ?? fallback).toString().trim();
}

function getGrade() {
  return ds("userGrade", window.currentUser?.grade || "");
}

function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") return (els.branchSelect?.value || "").trim();
  return ds("defaultBranch", window.currentUser?.branch || "");
}

function buildFetchPayload(ym) {
  return {
    ym,
    branch: getEffectiveBranch(),
    grade: getGrade(),
    level: ds("userLevel"),
    team_a: ds("teamA"),
    team_b: ds("teamB"),
    team_c: ds("teamC"),
  };
}

function q(row, name) {
  return row?.querySelector?.(`[name="${name}"]`) || null;
}

function val(el) {
  return (el?.value ?? "").toString().trim();
}

/** input/select 중 whichever exists */
function getSelectOrInputValue(row, name) {
  const s = row.querySelector(`select[name="${name}"]`);
  if (s) return val(s);
  const i = row.querySelector(`input[name="${name}"]`);
  return val(i);
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return { status: "error", message: `JSON 파싱 실패 (HTTP ${res.status})` };
  }
}

/* ==========================
   ✅ payload builder + validation
========================== */
function buildSaveRowsPayload() {
  const tbody = els.inputTable?.querySelector("tbody");
  const rows = tbody ? Array.from(tbody.querySelectorAll("tr.input-row")) : [];
  if (!rows.length) return { ok: false, message: "저장할 데이터가 없습니다." };

  const payload = [];
  const seenTargets = new Set();

  for (let idx = 0; idx < rows.length; idx++) {
    const row = rows[idx];
    const rowNo = idx + 1;

    const requester_id = val(q(row, "rq_id")) || (window.currentUser?.id ?? "").toString().trim();
    const target_id = val(q(row, "tg_id"));

    // ✅ 대상자 필수
    if (!target_id) {
      return { ok: false, message: `(${rowNo}행) 대상자를 선택해주세요.` };
    }

    // ✅ 중복 대상자 방지 (같은 tg_id 두 번 저장 방지)
    if (seenTargets.has(target_id)) {
      return { ok: false, message: `(${rowNo}행) 동일한 대상자가 중복 입력되었습니다.` };
    }
    seenTargets.add(target_id);

    const after_ftable = getSelectOrInputValue(row, "after_ftable");
    const after_ltable = getSelectOrInputValue(row, "after_ltable");

    // ✅ 변경후 테이블 필수(*)
    if (!after_ftable || !after_ltable) {
      return {
        ok: false,
        message: `(${rowNo}행) 변경후 손보/생보 테이블을 선택해주세요.`,
      };
    }

    payload.push({
      requester_id,
      target_id,

      before_ftable: val(q(row, "before_ftable")),
      before_frate: val(q(row, "before_frate")),
      before_ltable: val(q(row, "before_ltable")),
      before_lrate: val(q(row, "before_lrate")),

      after_ftable,
      after_frate: val(q(row, "after_frate")),

      after_ltable,
      after_lrate: val(q(row, "after_lrate")),

      memo: val(q(row, "memo")),
    });
  }

  if (!payload.length) return { ok: false, message: "저장할 데이터가 없습니다." };
  return { ok: true, payload };
}

/* ==========================
   ✅ main
========================== */
export async function saveRows() {
  if (!els.root || !els.inputTable) return;

  // utils.selectedYM이 "YYYY-MM" 형태로 주는 전제 유지
  const ym = selectedYM(els.yearSelect, els.monthSelect); // "YYYY-MM"
  const branch = getEffectiveBranch();

  const saveUrl = ds("saveUrl"); // data-save-url
  if (!ym) return alertBox("연도/월도를 선택해주세요.");
  if (!branch) return alertBox("지점을 선택해주세요.");
  if (!saveUrl) return alertBox("저장 URL이 설정되어 있지 않습니다. (data-save-url 확인)");

  const built = buildSaveRowsPayload();
  if (!built.ok) return alertBox(built.message);

  const { payload } = built;

  // ✅ 저장 요청 body
  const body = {
    rows: payload,
    month: ym, // 서버가 month 키로 받는 구조 유지
    part: (window.currentUser?.part || "").toString().trim(),
    branch,
  };

  showLoading("저장 중...");

  try {
    const res = await fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(body),
    });

    const data = await safeJson(res);

    if (!res.ok || data.status !== "success") {
      throw new Error(data.message || `저장 실패 (HTTP ${res.status})`);
    }

    alertBox(`✅ ${data.saved_count ?? payload.length}건 저장 완료`);

    // ✅ 입력 초기화
    resetInputSection();

    // ✅ 저장 후 재조회
    await fetchData(buildFetchPayload(ym));
  } catch (err) {
    console.error("❌ [rate/save] 오류:", err);
    alertBox(err?.message || "저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
