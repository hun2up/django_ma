// django_ma/static/js/partner/mange_rate/index.js

/**
 * ✅ 요율변경 요청 페이지 (Manage Rate)
 * ------------------------------------------------------------
 * - 초기 연도/월도 드롭다운 구성
 * - 부서/지점 로드 (superuser 전용)
 * - main_admin / sub_admin 자동조회
 * - 검색 버튼 → fetchData 호출
 * - 내용입력 섹션 버튼 이벤트 등록
 * - 테이블 확인 모달 기능
 * ------------------------------------------------------------
 */

import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2, alertBox, showLoading, hideLoading } from "./utils.js";
import { initInputRowEvents } from "./input_rows.js";

document.addEventListener("DOMContentLoaded", async () => {
  if (!els.root) return;

  try {
    /* =======================================================
       ✅ 기본 상수
    ======================================================= */
    const now = new Date();
    const thisYear = now.getFullYear();
    const thisMonth = now.getMonth() + 1;
    const grade = els.root.dataset.userGrade || "";
    const autoLoadGrades = ["main_admin", "sub_admin"];

    /* =======================================================
       ✅ 연도/월도 드롭다운 생성
    ======================================================= */
    const fillDropdown = (el, start, end, selected, suffix) => {
      if (!el) return;
      el.innerHTML = "";
      for (let v = start; v <= end; v++) {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = `${v}${suffix}`;
        el.appendChild(opt);
      }
      el.value = selected;
    };

    fillDropdown(els.yearSelect, thisYear - 1, thisYear + 1, thisYear, "년");
    fillDropdown(els.monthSelect, 1, 12, thisMonth, "월");

    /* =======================================================
       ✅ 내용입력 버튼 초기화
    ======================================================= */
    initInputRowEvents();

    /* =======================================================
       ✅ superuser용 부서/지점 로드
    ======================================================= */
    if (grade === "superuser" && window.loadPartsAndBranches) {
      window.loadPartsAndBranches("manage-rate");
    }

    /* =======================================================
       ✅ 검색 버튼 클릭 시
    ======================================================= */
    els.btnSearch?.addEventListener("click", () => {
      const ym = `${els.yearSelect.value}-${pad2(els.monthSelect.value)}`;
      const branch =
        (els.branchSelect && els.branchSelect.value) ||
        els.root.dataset.defaultBranch ||
        "";

      if (!ym || !branch) {
        alertBox("연도·월도 및 지점을 선택해주세요.");
        return;
      }

      fetchData({
        ym,
        branch,
        grade,
        level: els.root.dataset.userLevel || "",
        team_a: els.root.dataset.teamA || "",
        team_b: els.root.dataset.teamB || "",
        team_c: els.root.dataset.teamC || "",
      });
    });

    /* =======================================================
       ✅ main_admin / sub_admin 자동조회
    ======================================================= */
    if (autoLoadGrades.includes(grade)) {
      const ym = `${thisYear}-${pad2(thisMonth)}`;
      const branch = els.root.dataset.defaultBranch || "";
      setTimeout(() => {
        fetchData({
          ym,
          branch,
          grade,
          level: els.root.dataset.userLevel || "",
          team_a: els.root.dataset.teamA || "",
          team_b: els.root.dataset.teamB || "",
          team_c: els.root.dataset.teamC || "",
        });
      }, 600);
    }

    /* =======================================================
       ✅ 테이블 확인 버튼 (모달)
    ======================================================= */
    const btnCheck = document.getElementById("btnCheckTable");
    const modalBody = document.getElementById("tableCheckBody");
    const modalEl = document.getElementById("tableCheckModal");

    if (btnCheck && modalBody && modalEl) {
      btnCheck.addEventListener("click", async () => {
        try {
          let branch = "";
          const user = window.currentUser || {};

          if (grade === "superuser") {
            const selectEl = document.getElementById("branchSelect");
            branch = (selectEl?.value || "").trim();
          } else {
            branch = (user.branch || "").trim();
          }

          if (!branch) {
            alertBox("지점 정보가 없습니다. 부서/지점을 먼저 선택하세요.");
            return;
          }

          modalBody.innerHTML = `<div class="py-4 text-muted">불러오는 중...</div>`;
          const modal = new bootstrap.Modal(modalEl);
          modal.show();

          showLoading("지점별 테이블 불러오는 중...");

          const res = await fetch(`/partner/ajax_table_fetch/?branch=${encodeURIComponent(branch)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });

          hideLoading();

          if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
          const data = await res.json();

          if (data.status !== "success") throw new Error(data.message);
          if (!data.rows?.length) {
            modalBody.innerHTML = `<div class="py-4 text-muted">등록된 테이블이 없습니다.</div>`;
            return;
          }

          // ✅ 테이블 구성
          const html = `
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
              <table class="table table-sm table-bordered align-middle mb-0"
                    style="font-size: 0.9rem; table-layout: fixed; width: 100%; text-align: center;">
                <colgroup>
                  <col style="width: 70%;">
                  <col style="width: 30%;">
                </colgroup>
                <thead class="table-light">
                  <tr>
                    <th class="text-center">테이블명</th>
                    <th class="text-center">요율(%)</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.rows
                    .map(
                      (r) => `
                      <tr>
                        <td class="text-truncate" title="${r.table || "-"}">${r.table || "-"}</td>
                        <td class="text-center">${r.rate ?? "-"}</td>
                      </tr>`
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `;
          modalBody.innerHTML = html;
        } catch (err) {
          console.error("❌ [테이블 확인] 실패:", err);
          hideLoading();
          modalBody.innerHTML = `<div class="py-4 text-danger">테이블 정보를 불러오지 못했습니다.</div>`;
        }
      });
    }
  } catch (err) {
    console.error("❌ [manage_rate/index.js 초기화 오류]", err);
  }
});
