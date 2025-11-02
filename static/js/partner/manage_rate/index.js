// django_ma/static/js/partner/manage_rate/index.js

import { els } from "./dom_refs.js";
import { fetchData } from "./fetch.js";
import { pad2 } from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
  if (!els.root) return;

  const now = new Date();
  const thisYear = now.getFullYear();
  const thisMonth = now.getMonth() + 1;
  const grade = els.root.dataset.userGrade || "";

  /* =======================================================
     ✅ 연도/월도 드롭다운
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
     ✅ superuser용 부서/지점 로드
  ======================================================= */
  if (grade === "superuser" && window.loadPartsAndBranches) {
    window.loadPartsAndBranches("manage-rate");
  }

  /* =======================================================
     ✅ 검색 버튼
  ======================================================= */
  els.btnSearch?.addEventListener("click", () => {
    const ym = `${els.yearSelect.value}-${pad2(els.monthSelect.value)}`;
    const branch =
      (els.branchSelect && els.branchSelect.value) ||
      els.root.dataset.defaultBranch ||
      "";

    console.log("🔍 검색 실행:", { ym, branch });
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
     ✅ main_admin/sub_admin 자동조회
  ======================================================= */
  if (["main_admin", "sub_admin"].includes(grade)) {
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
     ✅ 테이블 확인 버튼
  ======================================================= */
  const btnCheck = document.getElementById("btnCheckTable");
  const modalBody = document.getElementById("tableCheckBody");

  if (btnCheck && modalBody) {
    btnCheck.addEventListener("click", async () => {
      let branch = "";
      const user = window.currentUser || {};

      if (grade === "superuser") {
        // ✅ superuser는 선택한 지점 사용
        const selectEl = document.getElementById("branchSelect");
        branch = (selectEl?.value || "").trim();
      } else {
        // ✅ 나머지는 자신의 지점
        branch = (user.branch || "").trim();
      }

      if (!branch) {
        alert("지점 정보가 없습니다. 부서/지점을 먼저 선택하세요.");
        return;
      }

      modalBody.innerHTML = `<div class="py-4 text-muted">불러오는 중...</div>`;
      const modal = new bootstrap.Modal(document.getElementById("tableCheckModal"));
      modal.show();

      try {
        const res = await fetch(`/partner/ajax/table-fetch/?branch=${encodeURIComponent(branch)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();

        if (data.status !== "success") throw new Error(data.message);
        if (!data.rows?.length) {
          modalBody.innerHTML = `<div class="py-4 text-muted">등록된 테이블이 없습니다.</div>`;
          return;
        }

        const html = `
          <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
            <table class="table table-sm table-bordered align-middle mb-0"
                  style="font-size: 0.9rem; table-layout: fixed; width: 100%; text-align: center;">
              <colgroup>
                <col style="width: 50%;">
                <col style="width: 20%;">
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
        console.error("❌ 테이블 조회 실패:", err);
        modalBody.innerHTML = `<div class="py-4 text-danger">테이블 정보를 불러오지 못했습니다.</div>`;
      }
    });
  }
});
