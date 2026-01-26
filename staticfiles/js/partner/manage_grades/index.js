// django_ma/static/js/partner/manage_grades/index.js

/* =========================================================
   Manage Grades (Final Refactor v2.1 + Channel Dropdown FIX)
   ---------------------------------------------------------
   ✅ Fix: "지점 로드 실패" (ReferenceError: channel is not defined)
      - part 변경 시 channelSelect.value를 매번 읽어 전달하도록 수정
   ✅ Robust fetchList()
      - res.ok와 JSON 파싱 성공 여부를 분리해서, 에러 메시지/형식 안정화
   ✅ DataTables 안정
      - BFCache/pageshow 재진입에도 destroy/re-init 안전
      - DataTables/XLSX 미로딩 시 graceful fallback
   ✅ CSRF robust (hidden input 우선 + cookie fallback)
   ✅ 중간관리자: 레벨 변경 + 삭제
   ✅ "중간관리자 추가" 모달: 검색 + 승격
========================================================= */
(function () {
  "use strict";

  /* -----------------------------
   * Utils
   * ----------------------------- */
  const U = {
    str(v) { return String(v ?? "").trim(); },
    qs(sel, root) { return (root || document).querySelector(sel); },
    qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); },
    escHtml(v) {
      const s = String(v ?? "");
      return s
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    },
    getCookie(name) {
      const value = `; ${document.cookie || ""}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(";").shift();
      return "";
    },
    buildUrl(base, params) {
      const url = new URL(base, window.location.origin);
      Object.entries(params || {}).forEach(([k, v]) => {
        if (v === undefined || v === null || String(v).trim() === "") return;
        url.searchParams.set(k, String(v));
      });
      return url.toString();
    },
    async parseJson(res) {
      const text = await res.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch { data = null; }
      return { ok: res.ok, status: res.status, data, text };
    },
    pickListPayload(d) {
      if (!d) return [];
      if (Array.isArray(d)) return d;
      if (Array.isArray(d.channels)) return d.channels;
      if (Array.isArray(d.parts)) return d.parts;
      if (Array.isArray(d.branches)) return d.branches;
      if (Array.isArray(d.data)) return d.data;
      return [];
    },
  };

  /* -----------------------------
   * Root / Context
   * ----------------------------- */
  function getRoot() {
    return document.getElementById("manage-grades");
  }

  function getCSRFToken() {
    const input =
      U.qs('#csrfForm input[name="csrfmiddlewaretoken"]') ||
      U.qs('input[name="csrfmiddlewaretoken"]');
    const fromInput = U.str(input?.value);
    if (fromInput) return fromInput;
    return U.str(U.getCookie("csrftoken"));
  }

  function showToast(message, isSuccess) {
    const toastElement = document.getElementById("statusToast");
    const toastTitle = document.getElementById("toastTitle");
    const toastBody = document.getElementById("toastBody");

    if (!toastElement || !toastTitle || !toastBody) {
      alert(message);
      return;
    }

    if (isSuccess) {
      toastTitle.textContent = "✅ 처리 성공";
      toastElement.classList.remove("text-bg-danger");
      toastElement.classList.add("text-bg-success");
    } else {
      toastTitle.textContent = "❌ 처리 실패";
      toastElement.classList.remove("text-bg-success");
      toastElement.classList.add("text-bg-danger");
    }

    toastBody.textContent = message;

    if (window.bootstrap?.Toast) new bootstrap.Toast(toastElement, { delay: 3000 }).show();
    else alert(message);
  }

  function isAllowedGrade(grade) {
    return grade === "superuser" || grade === "head";
  }

  function getContext() {
    const root = getRoot();
    const d = root?.dataset || {};
    return {
      root,
      userGrade: U.str(d.userGrade),
      userBranch: U.str(d.userBranch),

      // 현재 선택 상태(서버 렌더링 값)
      selectedChannel: U.str(d.selectedChannel),
      selectedPart: U.str(d.selectedPart),
      selectedBranch: U.str(d.selectedBranch),

      // dataset (urls)
      updateLevelUrl: U.str(d.updateLevelUrl),
      deleteSubadminUrl: U.str(d.deleteSubadminUrl),
      addSubadminUrl: U.str(d.addSubadminUrl),
      searchUrl: U.str(d.searchUrl || "/api/accounts/search-user/"),

      // superuser filter endpoints
      fetchChannelsUrl: U.str(d.fetchChannelsUrl || "/partner/ajax/fetch-channels/"),
      fetchPartsUrl: U.str(d.fetchPartsUrl || "/partner/ajax/fetch-parts/"),
      fetchBranchesUrl: U.str(d.fetchBranchesUrl || "/partner/ajax/fetch-branches/"),
    };
  }

  function canInitDataTables(ctx) {
    if (!isAllowedGrade(ctx.userGrade)) return false;
    if (!ctx.selectedPart || !ctx.selectedBranch) return false;
    if (ctx.userGrade === "superuser" && (!ctx.selectedPart || !ctx.selectedBranch)) return false;
    return true;
  }

  /* =========================================================
   * Channel → Part → Branch (Superuser filter card)
   *
   * IDs:
   * - channelSelect, partSelect, branchSelect, btnSearch
   * - hidden init: selectedChannelInit, selectedPartInit, selectedBranchInit
   ========================================================= */
  function getFilterEls() {
    return {
      channelSelect: document.getElementById("channelSelect"),
      partSelect: document.getElementById("partSelect"),
      branchSelect: document.getElementById("branchSelect"),
      btnSearch: document.getElementById("btnSearch"),
      selectedChannelInit: document.getElementById("selectedChannelInit"),
      selectedPartInit: document.getElementById("selectedPartInit"),
      selectedBranchInit: document.getElementById("selectedBranchInit"),
    };
  }

  function setSelectOptions(selectEl, options, placeholderText) {
    if (!selectEl) return;
    const ph = placeholderText ?? "선택";
    const opts = Array.isArray(options) ? options : [];
    selectEl.innerHTML =
      `<option value="">${U.escHtml(ph)}</option>` +
      opts.map(v => {
        const val = U.str(v);
        return `<option value="${U.escHtml(val)}">${U.escHtml(val)}</option>`;
      }).join("");
  }

  function updateSearchButtonState(partSelect, branchSelect, btnSearch) {
    if (!btnSearch) return;
    const ok = !!U.str(partSelect?.value) && !!U.str(branchSelect?.value);
    btnSearch.disabled = !ok;
  }

  async function fetchList(url) {
    const res = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const parsed = await U.parseJson(res);

    // HTTP 에러인데 JSON이 없거나, 메시지 추출 실패 시도
    if (!res.ok) {
      const msg =
        parsed.data?.message ||
        parsed.data?.error ||
        `HTTP ${parsed.status}`;
      throw new Error(msg);
    }

    return U.pickListPayload(parsed.data);
  }

  async function loadChannelsIntoSelect(ctx, channelSelect) {
    channelSelect.disabled = true;
    setSelectOptions(channelSelect, [], "불러오는 중...");

    const list = await fetchList(ctx.fetchChannelsUrl);
    const cleaned = list.map(v => U.str(v)).filter(Boolean);

    setSelectOptions(channelSelect, cleaned, "부문 선택");
    channelSelect.disabled = false;
    return cleaned;
  }

  async function loadPartsByChannel(ctx, channel, partSelect) {
    partSelect.disabled = true;
    setSelectOptions(partSelect, [], channel ? "불러오는 중..." : "부문을 먼저 선택하세요");
    if (!channel) return [];

    const url = U.buildUrl(ctx.fetchPartsUrl, { channel });
    const list = await fetchList(url);
    const cleaned = list.map(v => U.str(v)).filter(Boolean);

    setSelectOptions(partSelect, cleaned, "부서 선택");
    partSelect.disabled = false;
    return cleaned;
  }

  async function loadBranchesByPart(ctx, part, branchSelect, channel) {
    branchSelect.disabled = true;
    setSelectOptions(branchSelect, [], part ? "불러오는 중..." : "부서를 먼저 선택하세요");
    if (!part) return [];

    // channel은 서버가 필요 없으면 무시해도 됨(옵션)
    const url = U.buildUrl(ctx.fetchBranchesUrl, { part, channel });
    const list = await fetchList(url);
    const cleaned = list.map(v => U.str(v)).filter(Boolean);

    setSelectOptions(branchSelect, cleaned, "지점 선택");
    branchSelect.disabled = false;
    return cleaned;
  }

  async function initChannelPartBranchSelectors() {
    const ctx = getContext();
    if (ctx.userGrade !== "superuser") return;

    const els = getFilterEls();
    const { channelSelect, partSelect, branchSelect, btnSearch } = els;
    if (!channelSelect || !partSelect || !branchSelect) return;

    // 중복 바인딩 방지(BFCache)
    if (channelSelect.dataset.bound === "1") {
      updateSearchButtonState(partSelect, branchSelect, btnSearch);
      return;
    }
    channelSelect.dataset.bound = "1";

    // 초기값(hidden inputs)
    const initChannel = U.str(els.selectedChannelInit?.value);
    const initPart = U.str(els.selectedPartInit?.value);
    const initBranch = U.str(els.selectedBranchInit?.value);

    if (btnSearch) btnSearch.disabled = true;

    // 1) channel 로드
    try {
      await loadChannelsIntoSelect(ctx, channelSelect);
    } catch (e) {
      console.error("부문(channel) 로드 실패:", e);
      setSelectOptions(channelSelect, [], "부문 로드 실패");
      channelSelect.disabled = false;
      return;
    }

    // 2) channel 변경 → part 로드 → branch 리셋
    channelSelect.addEventListener("change", async () => {
      const channel = U.str(channelSelect.value);

      setSelectOptions(partSelect, [], channel ? "불러오는 중..." : "부문을 먼저 선택하세요");
      partSelect.disabled = true;

      setSelectOptions(branchSelect, [], "부서를 먼저 선택하세요");
      branchSelect.disabled = true;

      updateSearchButtonState(partSelect, branchSelect, btnSearch);

      try {
        await loadPartsByChannel(ctx, channel, partSelect);
      } catch (e) {
        console.error("부서(part) 로드 실패:", e);
        setSelectOptions(partSelect, [], "부서 로드 실패");
        partSelect.disabled = false;
      }
    });

    // 3) part 변경 → branch 로드  ✅ FIX: channel 변수 참조 제거
    partSelect.addEventListener("change", async () => {
      const part = U.str(partSelect.value);
      const channel = U.str(channelSelect.value); // ✅ 현재 channel을 매번 읽는다

      setSelectOptions(branchSelect, [], part ? "불러오는 중..." : "부서를 먼저 선택하세요");
      branchSelect.disabled = true;
      updateSearchButtonState(partSelect, branchSelect, btnSearch);

      try {
        await loadBranchesByPart(ctx, part, branchSelect, channel);
      } catch (e) {
        console.error("지점(branch) 로드 실패:", e);
        setSelectOptions(branchSelect, [], "지점 로드 실패");
        branchSelect.disabled = false;
      }
    });

    // 4) branch 변경 → 검색 enable
    branchSelect.addEventListener("change", () => {
      updateSearchButtonState(partSelect, branchSelect, btnSearch);
    });

    // 5) 초기값 적용(channel → part → branch)
    if (initChannel) {
      channelSelect.value = initChannel;

      try {
        await loadPartsByChannel(ctx, initChannel, partSelect);

        if (initPart) {
          partSelect.value = initPart;

          try {
            await loadBranchesByPart(ctx, initPart, branchSelect, initChannel);
            if (initBranch) branchSelect.value = initBranch;
          } catch (e) {
            console.warn("초기 branch 로드 실패:", e);
          }
        }
      } catch (e) {
        console.warn("초기 part 로드 실패:", e);
      }
    } else {
      setSelectOptions(partSelect, [], "부문을 먼저 선택하세요");
      partSelect.disabled = true;
      setSelectOptions(branchSelect, [], "부서를 먼저 선택하세요");
      branchSelect.disabled = true;
    }

    updateSearchButtonState(partSelect, branchSelect, btnSearch);
  }

  /* -----------------------------
   * DataTables helpers
   * ----------------------------- */
  function safeDestroyDataTable($table) {
    if (!$table || !$table.length) return;
    if (window.$?.fn?.DataTable && $.fn.DataTable.isDataTable($table)) {
      try {
        $table.DataTable().clear().destroy(true);
      } catch (e) {
        console.warn("DataTable destroy failed:", e);
      }
    }
  }

  function initTables() {
    const ctx = getContext();
    if (!canInitDataTables(ctx)) {
      console.log("DataTables 초기화 조건 불충족 — 생략");
      return;
    }

    if (!window.$ || !$.fn || !$.fn.DataTable) {
      console.warn("jQuery/DataTables가 로드되지 않았습니다. 테이블 초기화를 생략합니다.");
      return;
    }

    const $subTable = $("#subAdminTable");
    const $allTable = $("#allUserTable");

    const ajaxBase = U.str($allTable.data("ajax-base"));
    if (!ajaxBase) return console.warn("ajax-base 누락 — allUserTable 초기화 불가");

    const ajaxUrl = U.buildUrl(ajaxBase, { part: ctx.selectedPart, branch: ctx.selectedBranch });

    safeDestroyDataTable($subTable);
    safeDestroyDataTable($allTable);

    // ✅ 중간관리자 명단
    $subTable.DataTable({
      paging: true,
      searching: true,
      info: true,
      pageLength: 10,
      autoWidth: false,
      lengthMenu: [[10, 25, 50, 100], ["10명", "25명", "50명", "100명"]],
      language: {
        url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/ko.json",
        lengthMenu: "페이지당 인원 _MENU_",
        search: "검색:",
        zeroRecords: "표시할 데이터가 없습니다.",
        emptyTable: "해당 부서/지점의 중간관리자가 없습니다.",
        info: "총 _TOTAL_명 중 _START_–_END_ 표시",
        infoEmpty: "데이터 없음",
      },
      dom: `
        <'d-flex justify-content-between align-items-center mb-2'
          <'d-flex align-items-center gap-2'l>
          f
        >rtip
      `,
    });

    // ✅ 전체 사용자 목록 (Ajax)
    $allTable.DataTable({
      serverSide: true,
      processing: true,
      ajax: { url: ajaxUrl, type: "GET" },
      columns: [
        { data: "part" },
        { data: "branch" },
        { data: "name" },
        { data: "user_id" },
        { data: "position" },
        { data: "team_a" },
        { data: "team_b" },
        { data: "team_c" },
      ],
      pageLength: 10,
      autoWidth: false,
      lengthMenu: [[10, 25, 50, 100], ["10명", "25명", "50명", "100명"]],
      language: {
        url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/ko.json",
        lengthMenu: "페이지당 인원 _MENU_",
        search: "검색:",
        processing: "로딩 중...",
        zeroRecords: "표시할 데이터가 없습니다.",
        emptyTable: "표시할 데이터가 없습니다.",
      },
      dom: `
        <'d-flex justify-content-between align-items-center mb-2'
          <'d-flex align-items-center gap-2'lB>
          f
        >rtip
      `,
      buttons: [
        {
          text: "<i class='bi bi-download'></i> 엑셀 다운로드",
          className: "btn btn-success btn-sm",
          action: function () {
            // XLSX가 없다면 안내
            if (!window.XLSX?.utils) {
              alert("엑셀 라이브러리(XLSX)가 로드되지 않았습니다.");
              return;
            }

            const url = U.buildUrl(ajaxUrl, { length: 999999 });

            fetch(url, { credentials: "same-origin" })
              .then((res) => {
                if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
                return res.json();
              })
              .then((data) => {
                const list = Array.isArray(data?.data) ? data.data : [];
                if (!list.length) {
                  alert("다운로드할 데이터가 없습니다.");
                  return;
                }

                const rows = list.map((u) => ({
                  성명: u.name || "",
                  사번: u.user_id || "",
                  직급: u.position || "",
                  팀A: u.team_a || "",
                  팀B: u.team_b || "",
                  팀C: u.team_c || "",
                }));

                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(rows);
                XLSX.utils.book_append_sheet(wb, ws, "전체설계사명단");
                XLSX.writeFile(wb, "전체설계사명단.xlsx");
              })
              .catch((err) => {
                alert("엑셀 생성 중 오류가 발생했습니다.");
                console.error("엑셀 다운로드 오류:", err);
              });
          },
        },
        {
          text: "<i class='bi bi-upload'></i> 엑셀 업로드",
          className: "btn btn-success btn-sm",
          action: function () {
            document.getElementById("excelFile")?.click();
          },
        },
      ],
    });

    // ✅ Excel Upload bind (1회)
    const excelFile = document.getElementById("excelFile");
    const excelForm = document.getElementById("excelUploadForm");
    if (excelFile && excelForm && !excelFile.dataset.bound) {
      excelFile.dataset.bound = "1";
      excelFile.addEventListener("change", function () {
        if (!this.files.length) return;
        const fileName = this.files[0].name;
        if (confirm(`"${fileName}" 파일을 업로드하시겠습니까?`)) {
          excelForm.submit();
        } else {
          this.value = "";
        }
      });
    }
  }

  /* -----------------------------
   * API calls
   * ----------------------------- */
  function buildHeaders() {
    const csrf = getCSRFToken();
    const headers = {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Requested-With": "XMLHttpRequest",
    };
    if (csrf) headers["X-CSRFToken"] = csrf;
    return headers;
  }

  async function postForm(url, params) {
    if (!url) throw new Error("요청 URL이 비어 있습니다.");
    const res = await fetch(url, {
      method: "POST",
      headers: buildHeaders(),
      credentials: "same-origin",
      body: new URLSearchParams(params || {}),
    });

    const parsed = await U.parseJson(res);

    // 서버가 HTML(로그인 redirect 등)을 주는 케이스 방어
    if (!parsed.data) {
      console.error("서버가 JSON이 아닌 응답:", { status: parsed.status, text: parsed.text });
      throw new Error(`서버 응답이 JSON이 아닙니다. (${parsed.status})`);
    }

    if (!res.ok) {
      throw new Error(parsed.data?.error || parsed.data?.message || `요청 실패 (${res.status})`);
    }

    if (parsed.data.success === false || parsed.data.ok === false) {
      throw new Error(parsed.data?.error || parsed.data?.message || "처리 실패");
    }

    return parsed.data;
  }

  /* -----------------------------
   * Delegated handlers (Subadmin)
   * - level change
   * - delete
   * ----------------------------- */
  async function handleLevelChange(selectEl) {
    const ctx = getContext();
    const updateUrl = ctx.updateLevelUrl;

    const tr = selectEl.closest("tr");
    const userId = U.str(tr?.dataset?.userId || tr?.getAttribute("data-user-id"));
    const newLevel = U.str(selectEl.value);

    if (!userId) return showToast("user_id를 찾을 수 없습니다.", false);

    try {
      await postForm(updateUrl, { user_id: userId, level: newLevel });
      showToast(`레벨이 ${newLevel}로 변경되었습니다.`, true);
    } catch (err) {
      console.error("레벨 변경 오류:", err);
      showToast(err?.message || "서버 요청 중 오류가 발생했습니다.", false);
    }
  }

  async function handleSubadminDelete(btnEl) {
    const ctx = getContext();
    const deleteUrl = ctx.deleteSubadminUrl;

    const tr = btnEl.closest("tr");
    const userId =
      U.str(btnEl.dataset.userId) ||
      U.str(tr?.dataset?.userId || tr?.getAttribute("data-user-id"));

    const userName =
      U.str(btnEl.dataset.userName) ||
      U.str(tr?.dataset?.userName) ||
      "";

    if (!userId) return showToast("user_id를 찾을 수 없습니다.", false);

    const label = userName ? `[${userName}]` : `[${userId}]`;
    if (!confirm(`${label} 중간관리자를 삭제할까요?\n(계정은 유지되고 grade가 basic으로 변경됩니다.)`)) return;

    btnEl.disabled = true;

    try {
      await postForm(deleteUrl, { user_id: userId });

      const $subTable = window.$ ? $("#subAdminTable") : null;
      if ($subTable?.length && $.fn.DataTable?.isDataTable($subTable)) {
        const dt = $subTable.DataTable();
        dt.row($(tr)).remove().draw(false);
      } else if (tr) {
        tr.remove();
      }

      showToast("중간관리자가 삭제되었습니다. (grade=basic)", true);
    } catch (err) {
      console.error("삭제 오류:", err);
      showToast(err?.message || "삭제 처리 중 오류가 발생했습니다.", false);
      btnEl.disabled = false;
    }
  }

  function bindSubAdminDelegation() {
    const table = document.getElementById("subAdminTable");
    if (!table || table.dataset.bound) return;
    table.dataset.bound = "1";

    table.addEventListener("change", (e) => {
      const sel = e.target?.closest?.(".level-select");
      if (!sel) return;
      handleLevelChange(sel);
    });

    table.addEventListener("click", (e) => {
      const btn = e.target?.closest?.(".js-delete-subadmin");
      if (!btn) return;
      handleSubadminDelete(btn);
    });
  }

  /* -----------------------------
   * Add SubAdmin Modal
   * ----------------------------- */
  function openAddModal() {
    const modalEl = document.getElementById("addSubAdminModal");
    const keywordEl = document.getElementById("addSubAdminKeyword");
    const resultsEl = document.getElementById("addSubAdminResults");
    if (!modalEl) return;

    const ctx = getContext();

    if (ctx.userGrade === "superuser" && (!ctx.selectedPart || !ctx.selectedBranch)) {
      return alert("부서/지점을 선택 후 검색하세요.");
    }
    if (ctx.userGrade === "head" && !ctx.userBranch) {
      return alert("본인 지점 정보가 없습니다. 관리자에게 문의해주세요.");
    }

    if (keywordEl) keywordEl.value = "";
    if (resultsEl) {
      resultsEl.innerHTML = `<div class="text-center py-3 text-muted">검색어를 입력 후 검색하세요.</div>`;
    }

    if (window.bootstrap?.Modal) new bootstrap.Modal(modalEl).show();
    else modalEl.classList.add("show");
  }

  async function runAddSearch(keyword) {
    const ctx = getContext();
    const resultsEl = document.getElementById("addSubAdminResults");
    if (!resultsEl) return;

    resultsEl.innerHTML = `<div class="text-center py-3 text-muted">검색 중...</div>`;

    try {
      const url = new URL(ctx.searchUrl, window.location.origin);
      url.searchParams.set("q", keyword);

      // head는 지점 제한 검색
      if (ctx.userGrade === "head") {
        url.searchParams.set("scope", "branch");
      }

      const res = await fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json().catch(() => ({}));
      const list = Array.isArray(data?.results) ? data.results : [];

      if (!list.length) {
        resultsEl.innerHTML = `<div class="text-center py-3 text-danger">검색 결과가 없습니다.</div>`;
        return;
      }

      resultsEl.innerHTML = list.map((u0) => {
        const u = u0 || {};
        const name = U.escHtml(u.name || "");
        const id = U.escHtml(u.id || "");
        const branch = U.escHtml(u.branch || "");
        const part = U.escHtml(u.part || "");
        const regist = U.escHtml(u.regist || "");
        const enter = U.escHtml(u.enter || "-");
        const quit = U.escHtml(u.quit || "재직중");

        return `
          <button type="button"
                  class="list-group-item list-group-item-action addsub-result"
                  data-user-id="${U.escHtml(u.id)}"
                  data-user-name="${U.escHtml(u.name)}">
            <div class="d-flex justify-content-between">
              <span><strong>${name}</strong> (${id}) ${regist ? `(${regist})` : ""}</span>
              <small class="text-muted">${branch}</small>
            </div>
            <small class="text-muted">부서: ${part || "-"} / 입사일: ${enter} / 퇴사일: ${quit}</small>
          </button>
        `;
      }).join("");
    } catch (err) {
      console.error("검색 오류:", err);
      resultsEl.innerHTML = `<div class="text-center text-danger py-3">검색 실패</div>`;
    }
  }

  async function promoteToSubAdmin(userId) {
    const ctx = getContext();
    if (!ctx.addSubadminUrl) throw new Error("승격 URL이 설정되지 않았습니다.");
    return postForm(ctx.addSubadminUrl, { user_id: userId });
  }

  function bindAddSubAdminModal() {
    const ctx = getContext();
    if (!isAllowedGrade(ctx.userGrade)) return;

    const btn = document.getElementById("btnOpenAddSubAdmin");
    const form = document.getElementById("addSubAdminSearchForm");
    const keywordEl = document.getElementById("addSubAdminKeyword");
    const resultsEl = document.getElementById("addSubAdminResults");
    const modalEl = document.getElementById("addSubAdminModal");

    if (btn && !btn.dataset.bound) {
      btn.dataset.bound = "1";
      btn.addEventListener("click", openAddModal);
    }

    if (form && !form.dataset.bound) {
      form.dataset.bound = "1";
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const kw = U.str(keywordEl?.value);
        if (!kw) return alert("검색어를 입력하세요.");
        await runAddSearch(kw);
      });
    }

    if (resultsEl && !resultsEl.dataset.bound) {
      resultsEl.dataset.bound = "1";
      resultsEl.addEventListener("click", async (e) => {
        const item = e.target?.closest?.(".addsub-result");
        if (!item) return;

        const userId = U.str(item.dataset.userId);
        const userName = U.str(item.dataset.userName);
        if (!userId) return;

        if (!confirm(`[${userName || userId}] 사용자를 중간관리자(sub_admin)로 추가할까요?`)) return;

        try {
          await promoteToSubAdmin(userId);
          showToast("중간관리자로 추가되었습니다. (grade=sub_admin)", true);

          // 모달 닫기
          try {
            const inst = window.bootstrap?.Modal?.getInstance?.(modalEl);
            if (inst) inst.hide();
          } catch (_) {}

          window.location.reload();
        } catch (err) {
          console.error("승격 오류:", err);
          showToast(err?.message || "승격 처리 중 오류가 발생했습니다.", false);
        }
      });
    }

    if (modalEl && !modalEl.dataset.bound) {
      modalEl.dataset.bound = "1";
      modalEl.addEventListener("hidden.bs.modal", () => {
        if (keywordEl) keywordEl.value = "";
        if (resultsEl) resultsEl.innerHTML = `<div class="text-center py-3 text-muted">검색어를 입력 후 검색하세요.</div>`;
      });
    }
  }

  /* -----------------------------
   * init (with BFCache)
   * ----------------------------- */
  function initAll() {
    const ctx = getContext();
    if (!isAllowedGrade(ctx.userGrade)) return;

    initChannelPartBranchSelectors();
    initTables();
    bindSubAdminDelegation();
    bindAddSubAdminModal();
  }

  document.addEventListener("DOMContentLoaded", initAll);
  window.addEventListener("pageshow", (e) => { if (e.persisted) initAll(); });
})();
