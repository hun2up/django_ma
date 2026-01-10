// django_ma/static/js/partner/manage_efficiency/fetch.js
//
// ✅ Efficiency fetch + render (Accordion groups + rows) FINAL (REFAC)
// - grouped=1 응답(groups + rows 플랫) 지원
// - group_key(문자열) / group_pk(숫자) 둘 다로 매칭
// - ✅ sub_admin 그룹삭제 버튼 숨김
// - ✅ 그룹삭제/행삭제 이벤트 + 서버 POST + 재조회
// - ✅ superuser/main_admin: "각 행" 처리일자(date) 수정 가능 (즉시 저장)
// - ✅ 아코디언 헤더 내부 버튼 클릭 시 토글 방지(stopPropagation) 포함
// - ✅ 그룹 헤더: 스크롤 영역(eff-group-scroll) 안에 메타 + 확인서 버튼 포함

import { els } from "./dom_refs.js";
import { showLoading, hideLoading, alertBox, getCSRFToken } from "./utils.js";

const DEBUG = false;
const log = (...a) => DEBUG && console.log("[efficiency/fetch]", ...a);

/* =========================
   Small helpers
========================= */
function str(v) {
  return String(v ?? "").trim();
}
function numOrNull(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmtNumber(n) {
  const x = Number(n || 0);
  if (!Number.isFinite(x)) return "0";
  return x.toLocaleString("ko-KR");
}
function escapeHtml(s) {
  const t = str(s);
  return t
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function escapeAttr(s) {
  return escapeHtml(s);
}

/* =========================
   Root / Dataset helpers
========================= */
function getRoot() {
  return (
    els.root ||
    document.getElementById("manage-efficiency") ||
    document.getElementById("manage-calculate") ||
    document.getElementById("manage-rate") ||
    document.getElementById("manage-structure") ||
    null
  );
}

function getUserGrade() {
  const root = getRoot();
  const g1 = str(root?.dataset?.userGrade);
  const g2 = str(window?.currentUser?.grade);
  return g1 || g2;
}
function canAdminEdit() {
  const g = getUserGrade();
  return g === "superuser" || g === "main_admin";
}
function isSubAdmin() {
  return getUserGrade() === "sub_admin";
}

function getFetchUrl() {
  const root = getRoot();
  return str(root?.dataset?.dataFetchUrl || "");
}
function getDeleteRowUrl() {
  const root = getRoot();
  return str(root?.dataset?.dataDeleteRowUrl || "");
}
function getDeleteGroupUrl() {
  const root = getRoot();
  return str(root?.dataset?.dataDeleteGroupUrl || "");
}
function getUpdateProcessDateUrl() {
  const root = getRoot();
  const u1 = str(root?.dataset?.updateProcessDateUrl || "");
  const u2 = str(root?.dataset?.dataUpdateProcessDateUrl || "");
  const u3 = str(window?.ManageefficiencyBoot?.updateProcessDateUrl || "");
  return u1 || u2 || u3;
}

function getGroupsContainer() {
  return (
    els.groupsContainer ||
    document.getElementById("confirmGroupsAccordion") ||
    document.getElementById("confirmGroups") ||
    document.getElementById("efficiencyConfirmGroups") ||
    document.getElementById("groupsContainer") ||
    document.querySelector("[data-role='confirm-groups']") ||
    document.querySelector(".confirm-groups") ||
    null
  );
}

/* =========================
   ⭐ 컬럼 비율 설정 (MAIN TABLE)
========================= */
const MAIN_COL_KEYS = [
  "requester",
  "requester_id",
  "category",
  "amount",
  "tax",
  "ded",
  "pay",
  "content",
  "request_date",
  "process_date",
  "remove",
];

const DEFAULT_MAIN_COL_WIDTHS = {
  requester: 8,
  requester_id: 7,
  category: 8,
  amount: 8,
  tax: 6,
  ded: 10,
  pay: 10,
  content: 20,
  request_date: 7,
  process_date: 8,
  remove: 8,
};

function buildMainColGroup() {
  return `
    <colgroup>
      ${MAIN_COL_KEYS.map((k) => `<col data-col="${k}">`).join("")}
    </colgroup>
  `;
}

function applyMainColWidths(root, table) {
  if (!root || !table) return;

  let conf;
  try {
    conf = JSON.parse(root.dataset.mainColWidths || "{}");
    conf = { ...DEFAULT_MAIN_COL_WIDTHS, ...conf };
  } catch {
    conf = { ...DEFAULT_MAIN_COL_WIDTHS };
  }

  const entries = Object.entries(conf).filter(([, v]) => Number(v) > 0);
  const sum = entries.reduce((a, [, v]) => a + Number(v), 0);
  if (!sum) return;

  const ratios = {};
  for (const [k, v] of entries) {
    ratios[k] = (Number(v) / sum) * 100;
  }

  const thCount = table.querySelectorAll("thead th").length;
  const colCount = table.querySelectorAll("colgroup col[data-col]").length;
  if (thCount && colCount && thCount !== colCount) {
    console.warn("[efficiency] colgroup/th count mismatch", { thCount, colCount });
  }

  table.querySelectorAll("colgroup col[data-col]").forEach((col) => {
    const key = col.dataset.col;
    if (ratios[key]) col.style.width = `${ratios[key]}%`;
  });

  table.style.tableLayout = "fixed";
}

/* =========================
   그룹 타이틀 정규화
========================= */
function normalizeGroupTitle(rawTitle, fallbackMonth, fallbackBranch) {
  const title = str(rawTitle);

  if (title && title.includes(" - ")) {
    const parts = title
      .split(" - ")
      .map((x) => x.trim())
      .filter(Boolean);
    if (parts.length) return parts[parts.length - 1];
  }

  if (title) return title;

  const month = str(fallbackMonth);
  const branch = str(fallbackBranch);
  if (month && branch) return `${month} / ${branch}`;
  if (month) return month;
  if (branch) return branch;
  return "그룹";
}

/* =========================
   Normalize helpers
========================= */
function normalizeAttachment(a) {
  if (!a || typeof a !== "object") return {};
  return {
    id: a.id ?? a.pk ?? null,
    file: a.file ?? a.url ?? a.file_url ?? "",
    file_name: a.file_name ?? a.original_name ?? a.name ?? "",
  };
}

/**
 * ✅ row 그룹키 후보(문자열/숫자) 모두 흡수
 */
function pickRowGroupKeys(r) {
  const keys = [];

  // 문자열
  const sCandidates = [
    r?.group_key,
    r?.confirm_group_id,
    r?.confirm_group_key,
    r?.confirm_group__confirm_group_id,
  ];
  for (const c of sCandidates) {
    const v = str(c);
    if (v) keys.push(v);
  }

  // 숫자 pk
  const pkCandidates = [
    r?.group_pk,
    r?.confirm_group_pk,
    r?.confirm_group,
    r?.group_id,
    r?.group,
  ];
  for (const c of pkCandidates) {
    const n = numOrNull(c);
    if (n !== null) keys.push(String(n));
  }

  return Array.from(new Set(keys));
}

function normalizeRow(r) {
  if (!r || typeof r !== "object") return {};
  return {
    id: r.id ?? r.pk ?? null,
    group_keys: pickRowGroupKeys(r),
    requester_name: r.requester_name ?? r.requester ?? "",
    requester_id: r.requester_id ?? r.rq_id ?? r.requester_empno ?? "",
    category: r.category ?? "",
    amount: r.amount ?? 0,
    tax: r.tax ?? r.tax_amount ?? r.withholding_tax ?? null,
    ded_name: r.ded_name ?? "",
    ded_id: r.ded_id ?? "",
    pay_name: r.pay_name ?? "",
    pay_id: r.pay_id ?? "",
    content: r.content ?? "",
    request_date: r.request_date ?? r.created_at ?? "",
    process_date: r.process_date ?? "",
  };
}

/**
 * ✅ group_key(문자열)을 최우선
 */
function normalizeGroup(g) {
  if (!g || typeof g !== "object") return {};
  const attachments = Array.isArray(g.attachments)
    ? g.attachments.map(normalizeAttachment)
    : [];

  const groupKey = str(g.group_key || g.confirm_group_id || g.confirm_group_key || "");
  const groupPk = numOrNull(g.group_pk ?? g.id);

  return {
    group_key: groupKey,
    group_pk: groupPk,
    title: g.title ?? "",
    month: g.month ?? "",
    branch: g.branch ?? "",
    row_count: g.row_count ?? 0,
    total_amount: g.total_amount ?? 0,
    attachments,
  };
}

/* =========================
   rows -> groupKey 기준으로 묶기
========================= */
function buildRowsByGroup(rows) {
  const map = Object.create(null);
  const list = Array.isArray(rows) ? rows.map(normalizeRow) : [];

  for (const r of list) {
    const keys = Array.isArray(r.group_keys) ? r.group_keys : [];
    if (!keys.length) continue;

    for (const key of keys) {
      const k = str(key);
      if (!k) continue;
      if (!map[k]) map[k] = [];
      map[k].push(r);
    }
  }
  return map;
}

function sumAmount(list) {
  let s = 0;
  for (const r of list || []) {
    const n = Number(r?.amount || 0);
    if (Number.isFinite(n)) s += n;
  }
  return s;
}

/* =========================
   Confirm(확인서) 대표 첨부 1개 선택
========================= */
function pickPrimaryAttachment(group) {
  const atts = Array.isArray(group?.attachments) ? group.attachments : [];
  if (!atts.length) return { fileName: "", fileUrl: "", rawName: "", extraCount: 0 };

  const first = atts[0] || {};
  const rawName = str(first.file_name) || "확인서";
  const fileUrl = str(first.file);
  const extraCount = Math.max(0, atts.length - 1);

  const fileName = extraCount > 0 ? `${rawName} 외 ${extraCount}건` : rawName;
  return { fileName, fileUrl, rawName, extraCount };
}

/* =========================
   Row process_date cell
========================= */
function renderProcessDateCell(r) {
  const val = str(r.process_date);

  if (!canAdminEdit()) {
    return escapeHtml(val || "-");
  }

  return `
    <input type="date"
           class="form-control form-control-sm js-process-date"
           data-row-id="${escapeAttr(str(r.id))}"
           data-prev-value="${escapeAttr(val)}"
           value="${escapeAttr(val)}"
           style="min-width:135px;" />
  `;
}

/* =========================
   ✅ Events (delegation) — bind once
========================= */
function bindHandlersOnce() {
  const acc = getGroupsContainer();
  if (!acc) return;

  if (acc.dataset.boundHandlers === "1") return;
  acc.dataset.boundHandlers = "1";

  /* -------------------------------------------------------
     ✅ 0) 아코디언 헤더 내부 버튼 클릭 시 토글 방지
     - 확인서 확인 / 다운로드 / 삭제 버튼 클릭 시
       accordion-button까지 이벤트가 올라가면서 토글되는 문제 방지
     - "캡처링 단계(true)"에서 먼저 막는 게 가장 안정적
  -------------------------------------------------------- */
  acc.addEventListener(
    "click",
    (e) => {
      const btn = e.target.closest(".js-confirm-view, .js-confirm-download, .js-confirm-delete");
      if (!btn) return;
      e.stopPropagation(); // ✅ 토글 방지
    },
    true
  );

  /* -------------------------------------------------------
     ✅ 1) click: delete-row / delete-group (data-action)
  -------------------------------------------------------- */
  acc.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = str(btn.dataset.action);

    // ✅ 행 삭제
    if (action === "delete-row") {
      const url = getDeleteRowUrl();
      if (!url) return alertBox("행삭제 URL이 없습니다. (data-data-delete-row-url 확인)");

      const rowId = str(btn.dataset.rowId);
      if (!rowId) return alertBox("row_id가 없습니다.");

      if (!confirm("해당 행을 삭제할까요?")) return;

      showLoading("행 삭제 중...");
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ id: rowId }),
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || `삭제 실패(${res.status})`);
        }

        if (window.__lastEfficiencyYM && window.__lastEfficiencyBranch) {
          await fetchData(window.__lastEfficiencyYM, window.__lastEfficiencyBranch);
        }
      } catch (err) {
        console.error("❌ delete-row error:", err);
        alertBox(err?.message || "행 삭제 중 오류가 발생했습니다.");
      } finally {
        hideLoading();
      }
      return;
    }

    // ✅ 그룹 삭제
    if (action === "delete-group") {
      if (isSubAdmin()) return;

      const url = getDeleteGroupUrl();
      if (!url) return alertBox("그룹삭제 URL이 없습니다. (data-data-delete-group-url 확인)");

      const groupId = str(btn.dataset.groupId);
      if (!groupId) return alertBox("group_id가 없습니다.");

      if (!confirm("해당 그룹을 삭제할까요?\n(그룹 내 저장된 행 + 확인서도 함께 삭제됩니다)")) return;

      showLoading("그룹 삭제 중...");
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ group_id: groupId }),
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || `삭제 실패(${res.status})`);
        }

        if (window.__lastEfficiencyYM && window.__lastEfficiencyBranch) {
          await fetchData(window.__lastEfficiencyYM, window.__lastEfficiencyBranch);
        }
      } catch (err) {
        console.error("❌ delete-group error:", err);
        alertBox(err?.message || "그룹 삭제 중 오류가 발생했습니다.");
      } finally {
        hideLoading();
      }
    }
  });

  /* -------------------------------------------------------
     ✅ 2) change: process_date update (admin only)
  -------------------------------------------------------- */
  acc.addEventListener("change", async (e) => {
    const input = e.target;
    if (!input?.classList?.contains("js-process-date")) return;
    if (!canAdminEdit()) return;

    const url = getUpdateProcessDateUrl();
    if (!url) return alertBox("처리일자 저장 URL이 없습니다. (data-update-process-date-url 확인)");

    const rowId = str(input.dataset.rowId);
    if (!rowId) return alertBox("row_id가 없습니다.");

    const process_date = str(input.value); // ""이면 NULL 처리
    const prev = str(input.dataset.prevValue);

    input.disabled = true;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          id: rowId,
          process_date,
          kind: "efficiency",
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || `저장 실패(${res.status})`);
      }

      input.dataset.prevValue = process_date;
    } catch (err) {
      console.error("❌ update process_date error:", err);
      alertBox(err?.message || "처리일자 저장 중 오류가 발생했습니다.");

      // 실패 시 롤백
      input.value = prev;
    } finally {
      input.disabled = false;
    }
  });
}

/* =========================
   Render Groups (Accordion)
========================= */
function renderGroups(groups, rowsByGroup) {
  const acc = getGroupsContainer();
  if (!acc) {
    log("groups container not found -> skip renderGroups");
    return;
  }

  const canDeleteGroup = canAdminEdit();
  const subAdmin = isSubAdmin();

  const list = Array.isArray(groups) ? groups.map(normalizeGroup) : [];
  if (!list.length) {
    acc.innerHTML = `
      <div class="alert alert-secondary mb-0">
        표시할 지점효율 입력내용이 없습니다.
      </div>
    `;
    return;
  }

  const html = list
    .map((g, idx) => {
      const gid = str(g.group_key) || `g${idx}`;
      const gidPk = g.group_pk !== null ? String(g.group_pk) : "";

      const headingId = `heading_${escapeAttr(gid)}_${idx}`;
      const collapseId = `collapse_${escapeAttr(gid)}_${idx}`;

      const titleText = normalizeGroupTitle(g.title, g.month, g.branch);
      const headerTitle = escapeHtml(titleText);

      const rows = (rowsByGroup?.[gid] || []) || (gidPk ? rowsByGroup?.[gidPk] || [] : []);
      const rowCount = fmtNumber(g.row_count || rows.length || 0);
      const totalAmt = fmtNumber(
        (Number(g.total_amount) || 0) > 0 ? g.total_amount : sumAmount(rows)
      );

      const monthText = escapeHtml(str(g.month || ""));
      const branchText = escapeHtml(str(g.branch || ""));

      // ✅ 확인서(대표 첨부) 표시
      const { fileName, fileUrl, rawName } = pickPrimaryAttachment(g);
      const fileNameEsc = escapeAttr(fileName);
      const rawNameEsc = escapeAttr(rawName);

      // 다운로드 버튼(파일 없으면 disabled)
      const downloadBtnHtml = fileUrl
        ? `
          <a class="btn btn-outline-success btn-sm js-confirm-download"
             href="${escapeAttr(fileUrl)}"
             download="${rawNameEsc}"
             data-group-id="${escapeAttr(gid)}">
            다운로드
          </a>
        `
        : `
          <button type="button" class="btn btn-outline-success btn-sm js-confirm-download" disabled
                  data-group-id="${escapeAttr(gid)}">
            다운로드
          </button>
        `;

      // 그룹 삭제 버튼: sub_admin 숨김
      const deleteGroupBtnHtml = canDeleteGroup
        ? `
          <button type="button"
                  class="btn btn-outline-danger btn-sm js-confirm-delete"
                  data-action="delete-group"
                  data-group-id="${escapeAttr(gid)}"
                  style="white-space:nowrap;">
            삭제
          </button>
        `
        : ``;

      const rowsHtml = rows.length
        ? `
          <div class="table-responsive">
            <table class="table table-sm mb-0 main-group-table">
              ${buildMainColGroup()}
              <thead class="table-light">
                <tr>
                  <th class="text-center">요청자</th>
                  <th class="text-center">사번</th>
                  <th class="text-center">구분</th>
                  <th class="text-center">금액</th>
                  <th class="text-center">세액</th>
                  <th class="text-center">공제자</th>
                  <th class="text-center">지급자</th>
                  <th class="text-center td-content">내용</th>
                  <th class="text-center">요청일</th>
                  <th class="text-center">처리일자</th>
                  <th class="text-center">삭제</th>
                </tr>
              </thead>
              <tbody>
                ${rows
                  .map((r) => {
                    const rowId = str(r.id);

                    const amountNum = Number(r.amount || 0);

                    const taxFromServer = Number(r.tax);
                    const taxNum = Number.isFinite(taxFromServer)
                      ? taxFromServer
                      : (Number.isFinite(amountNum) ? Math.round(amountNum * 0.033) : 0);

                    const ded = `${escapeHtml(str(r.ded_name))}${
                      r.ded_id ? `(${escapeHtml(str(r.ded_id))})` : ""
                    }`.trim();

                    const pay = `${escapeHtml(str(r.pay_name))}${
                      r.pay_id ? `(${escapeHtml(str(r.pay_id))})` : ""
                    }`.trim();

                    const rowDeleteDisabled = subAdmin ? "disabled" : "";

                    const processDateCell = renderProcessDateCell(r);

                    // title에는 escape, 본문은 escapeHtml로 출력(ellipsis + hover 확장 대응)
                    const contentText = str(r.content);
                    const contentTitle = escapeAttr(contentText);
                    const contentBody = escapeHtml(contentText);

                    return `
                      <tr>
                        <td class="text-center">${escapeHtml(str(r.requester_name))}</td>
                        <td class="text-center">${escapeHtml(str(r.requester_id))}</td>
                        <td class="text-center">${escapeHtml(str(r.category))}</td>

                        <td class="text-end">${fmtNumber(amountNum)}</td>
                        <td class="text-end">${fmtNumber(taxNum)}</td>

                        <td class="text-center">${ded || "-"}</td>
                        <td class="text-center">${pay || "-"}</td>

                        <td class="td-content" title="${contentTitle}">${contentBody || "-"}</td>

                        <td class="text-center">${escapeHtml(str(r.request_date))}</td>

                        <td class="text-center">
                          ${processDateCell}
                        </td>

                        <td class="text-center">
                          <button type="button"
                                  class="btn btn-outline-danger btn-sm"
                                  data-action="delete-row"
                                  data-row-id="${escapeAttr(rowId)}"
                                  style="white-space:nowrap;"
                                  ${rowDeleteDisabled}>
                            삭제
                          </button>
                        </td>
                      </tr>
                    `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        : `
          <div class="text-muted small py-3 px-3">
            이 그룹에 저장된 행이 없습니다.
          </div>
        `;

      // ✅ 그룹 헤더(스크롤 영역 안에 메타 + 확인서 UI 포함)
      // - 아코디언 토글은 accordion-button 자체 클릭으로만 동작
      // - 내부 버튼들은 bindHandlersOnce()에서 stopPropagation 처리됨
      return `
        <div class="accordion-item">
          <h2 class="accordion-header" id="${headingId}">
            <button class="accordion-button collapsed" type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#${collapseId}"
                    aria-expanded="false"
                    aria-controls="${collapseId}">

              <div class="eff-group-scroll">
                <div class="eff-group-meta">
                  <span class="badge bg-light text-dark border">월도: ${monthText || "-"}</span>
                  <span class="badge bg-light text-dark border">소속: ${branchText || "-"}</span>
                  <span class="badge bg-light text-dark border">건수: ${rowCount}</span>
                  <span class="badge bg-light text-dark border">합계: ${totalAmt}</span>
                  <span class="badge bg-white text-dark border">${headerTitle}</span>
                </div>

                <div class="eff-group-confirm">
                  <button type="button"
                          class="btn btn-outline-secondary btn-sm js-confirm-view"
                          data-group-id="${escapeAttr(gid)}">
                    확인서 확인
                  </button>

                  <div class="input-group input-group-sm flex-nowrap" style="width:320px; max-width:320px;">
                    <span class="input-group-text bg-light" style="font-weight:600;">확인서</span>
                    <input type="text"
                           class="form-control text-truncate"
                           value="${fileNameEsc}"
                           placeholder="업로드 된 확인서 파일명"
                           readonly>
                  </div>

                  ${downloadBtnHtml}
                  ${deleteGroupBtnHtml}
                </div>
              </div>

            </button>
          </h2>

          <div id="${collapseId}" class="accordion-collapse collapse"
               aria-labelledby="${headingId}"
               data-bs-parent="#confirmGroupsAccordion">
            <div class="accordion-body p-0">
              ${rowsHtml}
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  acc.innerHTML = html;

  // ⭐ 렌더 후 컬럼비율 적용 (모든 그룹 테이블)
  const root = getRoot();
  acc.querySelectorAll("table.main-group-table").forEach((tbl) => {
    applyMainColWidths(root, tbl);
  });
}

/* =========================
   Public: fetchData
========================= */
export async function fetchData(ym, branch) {
  const url = getFetchUrl();
  if (!url) {
    alertBox("조회 URL이 없습니다. (data-data-fetch-url 확인)");
    return;
  }

  const month = str(ym);
  const br = str(branch);
  if (!month || !br) return;

  // ✅ 재조회용 캐시
  window.__lastEfficiencyYM = month;
  window.__lastEfficiencyBranch = br;

  showLoading("조회 중...");

  try {
    const fullUrl = `${url}?month=${encodeURIComponent(month)}&branch=${encodeURIComponent(
      br
    )}&grouped=1`;
    log("fetchData ->", fullUrl);

    const res = await fetch(fullUrl, {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
    if (payload.status !== "success") throw new Error(payload.message || "조회 실패");

    const groups = payload.groups || [];
    const rows = payload.rows || [];
    const rowsByGroup = buildRowsByGroup(rows);

    renderGroups(groups, rowsByGroup);

    // ✅ 이벤트(삭제/처리일자/토글방지) 1회 바인딩
    bindHandlersOnce();
  } catch (e) {
    console.error("❌ efficiency fetchData error:", e);
    alertBox(e?.message || "조회 중 오류가 발생했습니다.");
  } finally {
    hideLoading();
  }
}
