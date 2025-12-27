// django_ma/static/js/partner/manage_efficiency/index.js
// ======================================================
// 📘 지점효율 페이지 - 초기화(index) 스캐폴딩
// - manage_rate/index.js 패턴과 동일
// - superuser 부서/지점 선택 후 검색
// - main_admin/sub_admin은 defaultBranch 기반 자동조회 가능하도록 설계
// ======================================================

import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2, selectedYM } from "../../common/manage/ym.js";

/* ==========================
   dataset helpers
========================== */
function ds(key, fallback = "") {
  return (els.root?.dataset?.[key] ?? fallback).toString().trim();
}

function getGrade() {
  return ds("userGrade", window.currentUser?.grade || "");
}

function getDefaultBranch() {
  return ds("defaultBranch", window.currentUser?.branch || "");
}

function getEffectiveBranch() {
  const grade = getGrade();
  if (grade === "superuser") return (els.branchSelect?.value || "").trim();
  return getDefaultBranch();
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

function alertBox(msg) {
  window.alert(msg);
}

/* ==========================
   period dropdown
========================== */
function fillDropdown(el, start, end, selected, suffix) {
  if (!el) return;
  el.innerHTML = "";
  for (let v = start; v <= end; v++) {
    const opt = document.createElement("option");
    opt.value = String(v);
    opt.textContent = `${v}${suffix}`;
    el.appendChild(opt);
  }
  el.value = String(selected);
}

function initPeriodDropdowns() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  fillDropdown(els.yearSelect, y - 1, y + 1, y, "년");
  fillDropdown(els.monthSelect, 1, 12, m, "월");
}

/* ==========================
   search
========================== */
async function runSearch({ ym, branch } = {}) {
  const finalYM = ym || selectedYM(els.yearSelect, els.monthSelect);
  const finalBranch = branch || getEffectiveBranch();

  if (!finalYM || !finalBranch) {
    alertBox("연도·월도 및 지점을 선택해주세요.");
    return;
  }

  try {
    await fetchData(buildFetchPayload(finalYM));
  } catch (err) {
    console.error("❌ [efficiency/index] fetchData 실패:", err);
    alertBox("데이터 조회 중 오류가 발생했습니다.");
  }
}

function initSearchButton() {
  if (!els.btnSearch) return;
  els.btnSearch.addEventListener("click", () => runSearch());
}

/* ==========================
   superuser part/branch loader
========================== */
function initSuperuserPartsBranches() {
  if (getGrade() !== "superuser") return;
  if (typeof window.loadPartsAndBranches !== "function") return;
  // ✅ part_branch_selector.js가 제공하는 전역 함수가 있다면 사용
  window.loadPartsAndBranches("manage-efficiency");
}

/* ==========================
   autoload (main_admin/sub_admin)
========================== */
function initAutoLoad() {
  const grade = getGrade();
  if (!["main_admin", "sub_admin"].includes(grade)) return;

  const now = new Date();
  const ym = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
  const branch = getEffectiveBranch();
  if (!branch) return;

  setTimeout(() => runSearch({ ym, branch }), 250);
}

/* ==========================
   init
========================== */
function init() {
  if (!els.root) return;

  initPeriodDropdowns();
  initSuperuserPartsBranches();
  initSearchButton();
  initAutoLoad();
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    init();
  } catch (err) {
    console.error("❌ [manage_efficiency/index.js 초기화 오류]", err);
  }
});

export { runSearch };
