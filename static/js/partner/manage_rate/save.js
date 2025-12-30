// django_ma/static/js/partner/manage_rate/save.js
// ======================================================
// ✅ 요율변경 저장 (안전형) - month/branch 확정 + fetchData 호출 방식 수정
// ======================================================

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, pad2 } from "./utils.js";
import { fetchData } from "./fetch.js";
import { resetInputSection } from "./input_rows.js";

import { getCSRFToken } from "../../common/manage/csrf.js";

/* ======================================================
   URL helpers (dataset 키 불일치/과거버전 호환)
====================================================== */
function toDashed(camel) {
  return String(camel || "").replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);
}

function pickUrl(root, keys = [], fallback = "") {
  if (!root) return fallback;

  const ds = root.dataset || {};
  for (const k of keys) {
    const v = ds?.[k];
    if (v && String(v).trim()) return String(v).trim();
  }

  for (const k of keys) {
    const attr = `data-${toDashed(k)}`;
    const v = root.getAttribute?.(attr);
    if (v && String(v).trim()) return String(v).trim();
  }

  return fallback;
}

function getSaveUrl() {
  const root =
    els?.root ||
    document.getElementById("manage-rate") ||
    document.querySelector("[id='manage-rate']");

  return pickUrl(root, ["saveUrl", "dataSaveUrl", "dataDataSaveUrl"], "");
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/* ======================================================
   ✅ manage_rate 고정: month / branch 확정 로직
====================================================== */
function getGrade(root) {
  return String(root?.dataset?.userGrade || window.currentUser?.grade || "").trim();
}

function getEffectiveBranch(root) {
  const grade = getGrade(root);

  // superuser만 branchSelect 사용
  if (grade === "superuser") {
    const v = String(els.branchSelect?.value || document.getElementById("branchSelect")?.value || "").trim();
    if (v) return v;
  }

  // 그 외는 defaultBranch/user.branch 우선
  return (
    String(root?.dataset?.defaultBranch || "").trim() ||
    String(window.currentUser?.branch || "").trim() ||
    ""
  );
}

function getEffectiveYM(root) {
  // ✅ dom_refs에 year/month가 없고 yearSelect/monthSelect만 있는 케이스 방어
  const y =
    String(els.yearSelect?.value || document.getElementById("yearSelect")?.value || "").trim() ||
    String(root?.dataset?.selectedYear || "").trim();

  const mRaw =
    String(els.monthSelect?.value || document.getElementById("monthSelect")?.value || "").trim() ||
    String(root?.dataset?.selectedMonth || "").trim();

  const m = pad2(mRaw);
  const ym = `${y}-${m}`;

  // 형식 검증
  if (!/^\d{4}-\d{2}$/.test(ym)) return "";
  return ym;
}

/* ======================================================
   Payload build
====================================================== */
function buildPayloadFromRows(rows) {
  const payload = [];
  const seenTargets = new Set();

  for (const row of rows) {
    const rq_id = row.querySelector("[name='rq_id']")?.value.trim() || "";
    const rq_name = row.querySelector("[name='rq_name']")?.value.trim() || "";

    const tg_id = row.querySelector("[name='tg_id']")?.value.trim() || "";
    const tg_name = row.querySelector("[name='tg_name']")?.value.trim() || "";

    const after_ftable = row.querySelector("[name='after_ftable']")?.value.trim() || "";
    const after_ltable = row.querySelector("[name='after_ltable']")?.value.trim() || "";
    const memo = row.querySelector("[name='memo']")?.value.trim() || "";

    if (!tg_id) {
      alertBox("대상자를 선택해주세요.");
      return null;
    }
    if (!after_ftable || !after_ltable) {
      alertBox("변경후 손보/생보 테이블은 필수입니다.");
      return null;
    }

    if (seenTargets.has(tg_id)) {
      alertBox(`중복 대상자가 있습니다: ${tg_name || tg_id}`);
      return null;
    }
    seenTargets.add(tg_id);

    payload.push({
      requester_id: rq_id,
      requester_name: rq_name,
      target_id: tg_id,
      target_name: tg_name,
      after_ftable,
      after_ltable,
      memo,
    });
  }

  if (!payload.length) {
    alertBox("저장할 데이터가 없습니다.");
    return null;
  }
  return payload;
}

/* ======================================================
   ✅ Save
====================================================== */
export async function saveRows() {
  const root = els?.root || document.getElementById("manage-rate");
  const saveUrl = getSaveUrl();

  if (!saveUrl || saveUrl.includes("undefined")) {
    alertBox("저장 URL을 찾지 못했습니다. (data-save-url 확인)");
    return;
  }

  const rows = Array.from(els.inputTable?.querySelectorAll("tbody tr.input-row") || []);
  const payloadRows = buildPayloadFromRows(rows);
  if (!payloadRows) return;

  const month = getEffectiveYM(root);
  const branch = getEffectiveBranch(root);
  const part = String(window.currentUser?.part || "").trim();

  if (!month) {
    alertBox("월 정보가 올바르지 않습니다. (연도/월도 선택 상태 확인)");
    return;
  }
  if (!branch) {
    alertBox("지점 정보가 없습니다. (superuser는 지점을 선택해야 합니다)");
    return;
  }

  showLoading("저장 중...");

  try {
    const body = { rows: payloadRows, month, branch, part };

    console.log("➡️ [rate/save] url:", saveUrl);
    console.log("🧾 [rate/save] payload:", body);

    const res = await fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });

    const text = await res.text();
    console.log("📦 [rate/save] Raw Response:", text);

    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);

    const result = safeJsonParse(text);
    if (!result) throw new Error("서버 응답 파싱 실패(JSON 아님)");

    const ok = result.status === "success" || result.success === true || result.ok === true;
    if (!ok) {
      alertBox(result.message || "저장 중 오류가 발생했습니다.");
      return;
    }

    const count = result.saved_count ?? result.count ?? payloadRows.length;
    alertBox(`✅ ${count}건 저장 완료`);

    resetInputSection();

    // ✅ 핵심: fetchData는 payload 객체로 호출해야 함
    await fetchData({
      ym: month,
      branch,
      grade: getGrade(root),
      level: String(root?.dataset?.userLevel || "").trim(),
      team_a: String(root?.dataset?.teamA || "").trim(),
      team_b: String(root?.dataset?.teamB || "").trim(),
      team_c: String(root?.dataset?.teamC || "").trim(),
    });
  } catch (err) {
    console.error("❌ rate/save error:", err);
    alertBox(err?.message || "저장 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
