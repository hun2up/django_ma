// static/js/dash/dash_sales_page.js
(function () {
  "use strict";

  // =========================================================
  // JSON helpers
  // =========================================================
  function safeJsonFromScriptTag(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent || "");
    } catch (e) {
      return fallback;
    }
  }

  // =========================================================
  // Logging / Debug (once)
  // =========================================================
  function getStaticVer() {
    const root = document.getElementById("dash-sales");
    return (root?.dataset?.staticVersion || "dev").trim();
  }

  function debugOnce(payload) {
    if (window.__dashSalesDebugOnce) return;
    window.__dashSalesDebugOnce = true;
    try {
      console.log("[dash_sales_page] debug once", payload);
    } catch (e) {}
  }

  // =========================================================
  // Part -> Branch sync
  // =========================================================
  function initPartBranchSync(root) {
    const partEl = document.getElementById("partSelect");
    const branchEl = document.getElementById("branchSelect");
    if (!partEl || !branchEl) return;

    const partBranchMap = safeJsonFromScriptTag("part-branch-map", {});
    const branchAll = safeJsonFromScriptTag("branch-options-all", []);

    const initialPart = (root?.dataset?.initialPart || "").trim();
    const initialBranch = (root?.dataset?.initialBranch || "").trim();

    function rebuildBranchOptions(branches, selected) {
      branchEl.innerHTML = "";

      const optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "전체";
      optAll.selected = !selected;
      branchEl.appendChild(optAll);

      (branches || []).forEach((b) => {
        const v = (b || "").trim();
        if (!v) return;
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        opt.selected = selected === v;
        branchEl.appendChild(opt);
      });
    }

    function syncBranches(forceSelected) {
      const part = (partEl.value || "").trim();
      const selected = (forceSelected || branchEl.value || initialBranch || "").trim();

      if (!part) {
        rebuildBranchOptions(branchAll, branchAll.includes(selected) ? selected : "");
        return;
      }

      const branches = partBranchMap[part] || [];
      rebuildBranchOptions(branches, branches.includes(selected) ? selected : "");
    }

    // init
    if (initialPart) partEl.value = initialPart;
    syncBranches(initialBranch);

    partEl.addEventListener("change", function () {
      branchEl.value = ""; // 부서 바뀌면 지점은 전체로
      syncBranches("");
    });
  }

  // =========================================================
  // Life_nl -> Insurer sync (즉시 연동)
  // =========================================================
  function initLifeNlInsurerSync(root) {
    const lifeEl = document.getElementById("lifeNlSelect");
    const insurerEl = document.getElementById("insurerSelect");
    if (!lifeEl || !insurerEl) return;

    const map = safeJsonFromScriptTag("life-nl-insurer-map", {});
    const initialLifeNl = (root?.dataset?.initialLifeNl || "").trim();
    const initialInsurer = (root?.dataset?.initialInsurer || "").trim();

    function uniqClean(arr) {
      const out = [];
      const seen = new Set();
      (arr || []).forEach((x) => {
        const v = (x || "").trim();
        if (!v) return;
        if (seen.has(v)) return;
        seen.add(v);
        out.push(v);
      });
      return out;
    }

    function rebuildInsurerOptions(insurers, selected) {
      insurerEl.innerHTML = "";

      const optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "전체";
      optAll.selected = !selected;
      insurerEl.appendChild(optAll);

      (insurers || []).forEach((ins) => {
        const v = (ins || "").trim();
        if (!v) return;
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        opt.selected = selected === v;
        insurerEl.appendChild(opt);
      });
    }

    function getInsurersByLifeNl(lifeNl) {
      const ln = (lifeNl || "").trim();
      if (!ln) {
        const all = [].concat(map["손보"] || [], map["생보"] || [], map["자동차"] || []);
        return uniqClean(all);
      }
      return uniqClean(map[ln] || []);
    }

    function syncInsurers(forceSelected) {
      const ln = (lifeEl.value || "").trim();
      const insurers = getInsurersByLifeNl(ln);

      const selected = (forceSelected || insurerEl.value || initialInsurer || "").trim();
      const finalSelected = insurers.includes(selected) ? selected : "";
      rebuildInsurerOptions(insurers, finalSelected);
    }

    // init
    if (initialLifeNl && !lifeEl.value) lifeEl.value = initialLifeNl;
    syncInsurers(initialInsurer);

    lifeEl.addEventListener("change", function () {
      insurerEl.value = "";
      syncInsurers("");
    });
  }

  // =========================================================
  // Chart helpers
  // =========================================================
  function showWarnById(warnId, msg) {
    const warnEl = document.getElementById(warnId);
    if (!warnEl) return;
    warnEl.style.display = "block";
    warnEl.textContent = msg;
  }

  function hideWarnById(warnId) {
    const warnEl = document.getElementById(warnId);
    if (!warnEl) return;
    warnEl.style.display = "none";
    warnEl.textContent = "";
  }

  function destroyChart(chartKey) {
    const inst = window[chartKey];
    if (!inst) return;
    try {
      inst.destroy();
    } catch (e) {}
    window[chartKey] = null;
  }

  function toDayOfMonthLabels(dateLabels) {
    return (dateLabels || []).map((s) => {
      const m = String(s || "").match(/-(\d{2})$/);
      if (!m) return s;
      return String(parseInt(m[1], 10));
    });
  }

  // ✅ "마지막 영수일자"를 cumsum의 마지막 '증가' 지점으로 추정하고 이후 null
  function trimAfterLastIncreaseToNull(cumsum) {
    if (!Array.isArray(cumsum) || cumsum.length === 0) return cumsum;

    let lastIdx = -1;
    for (let i = 0; i < cumsum.length; i++) {
      const cur = Number(cumsum[i] ?? 0);
      const prev = i === 0 ? 0 : Number(cumsum[i - 1] ?? 0);
      if (cur - prev !== 0) lastIdx = i;
    }

    // 전부 증가 없음(=월 전체 0) -> 전부 null (원치 않으면 return cumsum;)
    if (lastIdx < 0) return cumsum.map(() => null);

    return cumsum.map((v, i) => (i <= lastIdx ? v : null));
  }

  function hasAnyIncrease(cumsum) {
    if (!Array.isArray(cumsum) || cumsum.length === 0) return false;
    for (let i = 0; i < cumsum.length; i++) {
      const cur = Number(cumsum[i] ?? 0);
      const prev = i === 0 ? 0 : Number(cumsum[i - 1] ?? 0);
      if (cur - prev !== 0) return true;
    }
    return false;
  }

  // =========================================================
  // Render chart (2 datasets: 당월 + 전월)
  // =========================================================
  function normalizeSeriesToLen(arr, len) {
    // arr이 없거나 배열이 아니면 전부 null
    if (!Array.isArray(arr) || arr.length === 0) return new Array(len).fill(null);

    // 길이가 맞으면 그대로
    if (arr.length === len) return arr;

    // 길이가 다르면: 짧으면 null로 패딩, 길면 자르기
    if (arr.length < len) return arr.concat(new Array(len - arr.length).fill(null));
    return arr.slice(0, len);
  }

  function renderCompareLineChart(opts) {
    const {
      canvasId,
      warnId,
      chartKey,
      thisMonthScriptId,
      prevMonthScriptId,
      yearAgoScriptId,               // ✅ 추가
      yearAgoLabel, 
      thisLabel,
      prevLabel,
      useNlLifeUnifiedYAxis,
      trimAfterLast,
    } = opts;

    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const rawLabels = safeJsonFromScriptTag("chart-day-labels", []);
    const labels = toDayOfMonthLabels(rawLabels);
    const len = labels.length;

    const rawThis = safeJsonFromScriptTag(thisMonthScriptId, []);
    const rawPrev = safeJsonFromScriptTag(prevMonthScriptId, []);
    const rawYA   = yearAgoScriptId ? safeJsonFromScriptTag(yearAgoScriptId, []) : [];

    const fixedYA   = normalizeSeriesToLen(rawYA, len);

    const dataYA   = trimAfterLast ? trimAfterLastIncreaseToNull(fixedYA) : fixedYA;

    if (!Array.isArray(labels) || len === 0) {
      showWarnById(warnId, "차트 라벨(월 1~말일)이 없습니다.");
      return;
    }

    // ✅ 당월은 반드시 len과 일치해야 함(당월이 깨지면 렌더 불가)
    if (!Array.isArray(rawThis) || rawThis.length !== len) {
      showWarnById(
        warnId,
        "당월 차트 데이터 길이가 라벨과 일치하지 않습니다. (labels=" +
          len +
          ", data=" +
          (Array.isArray(rawThis) ? rawThis.length : "N/A") +
          ")"
      );
      return;
    }

    // ✅ 전월은 “없어도 렌더”하도록 보정
    const fixedPrev = normalizeSeriesToLen(rawPrev, len);

    if (typeof window.Chart === "undefined") {
      showWarnById(warnId, "Chart.js 로드에 실패했습니다. (정적 파일 경로/collectstatic 여부 확인)");
      return;
    }

    const dataThis = trimAfterLast ? trimAfterLastIncreaseToNull(rawThis) : rawThis;
    const dataPrev = trimAfterLast ? trimAfterLastIncreaseToNull(fixedPrev) : fixedPrev;

    const anyThis = hasAnyIncrease(rawThis);
    const anyPrev = hasAnyIncrease(fixedPrev);

    if (!anyThis && !anyPrev) showWarnById(warnId, "당월/전월 모두 매출이 0입니다.");
    else if (!anyThis && anyPrev) showWarnById(warnId, "당월 매출이 0입니다. (전월은 데이터 있음)");
    else if (anyThis && !anyPrev) showWarnById(warnId, "전월 데이터가 없습니다. (당월은 정상 표시)");
    else hideWarnById(warnId);

    destroyChart(chartKey);

    const nlStep = safeJsonFromScriptTag("nl-l-y-step", null);
    const nlMax = safeJsonFromScriptTag("nl-l-y-max", null);

    const yScale = { ticks: { callback: (v) => Number(v).toLocaleString() } };
    if (useNlLifeUnifiedYAxis && typeof nlStep === "number" && typeof nlMax === "number") {
      yScale.beginAtZero = true;
      yScale.suggestedMax = nlMax;
      yScale.ticks = { stepSize: nlStep, callback: (v) => Number(v).toLocaleString() };
    }

    const ctx = canvas.getContext("2d");
    window[chartKey] = new window.Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: thisLabel || "당월", data: dataThis, tension: 0.25, pointRadius: 2, borderWidth: 2,
            borderColor: "rgb(54, 162, 235)", backgroundColor: "rgba(54, 162, 235, 0.15)", spanGaps: false },

          { label: prevLabel || "전월", data: dataPrev, tension: 0.25, pointRadius: 2, borderWidth: 2,
            borderDash: [6, 4],
            borderColor: "rgb(75, 192, 192)", backgroundColor: "rgba(75, 192, 192, 0.15)", spanGaps: false },

          // ✅ 전년도
          { label: yearAgoLabel || "전년도", data: dataYA, tension: 0.25, pointRadius: 2, borderWidth: 2,
            borderDash: [2, 4],
            borderColor: "rgb(153, 102, 255)", backgroundColor: "rgba(153, 102, 255, 0.12)", spanGaps: false },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                const v = ctx?.parsed?.y;
                const label = ctx?.dataset?.label || "";
                if (v === null || typeof v === "undefined") return label + ": -";
                return label + ": " + Number(v || 0).toLocaleString();
              },
            },
          },
        },
        scales: { y: yScale },
      },
    });
  }

  // =========================================================
  // Charts init
  // =========================================================
  function initCharts() {
    const rawLabels = safeJsonFromScriptTag("chart-day-labels", []);

    const sLong = safeJsonFromScriptTag("chart-cumsum", []);
    const sCar = safeJsonFromScriptTag("car-chart-cumsum", []);
    const sNl = safeJsonFromScriptTag("nonlife-chart-cumsum", []);
    const sLife = safeJsonFromScriptTag("life-chart-cumsum", []);

    const pLong = safeJsonFromScriptTag("prev-chart-cumsum", []);
    const pCar = safeJsonFromScriptTag("prev-car-chart-cumsum", []);
    const pNl = safeJsonFromScriptTag("prev-nonlife-chart-cumsum", []);
    const pLife = safeJsonFromScriptTag("prev-life-chart-cumsum", []);

    const prevYm = safeJsonFromScriptTag("prev-ym", null); // 템플릿에서 json_script로 내려오면 OK
    // json_script가 아니라 context 문자열로만 넣는 경우 대비: dataset에서 읽기
    const root = document.getElementById("dash-sales");
    const prevYm2 = (root?.dataset?.prevYm || "").trim();

    const pyLong = safeJsonFromScriptTag("py-chart-cumsum", []);
    const pyCar  = safeJsonFromScriptTag("py-car-chart-cumsum", []);
    const pyNl   = safeJsonFromScriptTag("py-nonlife-chart-cumsum", []);
    const pyLife = safeJsonFromScriptTag("py-life-chart-cumsum", []);
    const prevYearYm = safeJsonFromScriptTag("prev-year-ym", null);

    debugOnce({
      staticVer: getStaticVer(),
      chartJsLoaded: typeof window.Chart !== "undefined",
      labelsLen: Array.isArray(rawLabels) ? rawLabels.length : "N/A",
      seriesLens: {
        long: Array.isArray(sLong) ? sLong.length : "N/A",
        car: Array.isArray(sCar) ? sCar.length : "N/A",
        nonlife: Array.isArray(sNl) ? sNl.length : "N/A",
        life: Array.isArray(sLife) ? sLife.length : "N/A",
      },
      prevSeriesLens: {
        long: Array.isArray(pLong) ? pLong.length : "N/A",
        car: Array.isArray(pCar) ? pCar.length : "N/A",
        nonlife: Array.isArray(pNl) ? pNl.length : "N/A",
        life: Array.isArray(pLife) ? pLife.length : "N/A",
      },
      prevYm: prevYm || prevYm2 || null,
    });

    const prevTag = (prevYm || prevYm2) ? String(prevYm || prevYm2) : "전월";

    // ✅ 당월 + 전월 비교(모두 마지막 영수일자 이후 null로 끊기)
    renderCompareLineChart({
      canvasId: "dailyCumsumChart",
      warnId: "chartWarn",
      chartKey: "__dailyCumsumChart",
      thisMonthScriptId: "chart-cumsum",
      prevMonthScriptId: "prev-chart-cumsum",
      yearAgoScriptId: "py-chart-cumsum",  
      thisLabel: "당월매출(손생)",
      prevLabel: `전월매출(손생)`,
      yearAgoLabel: `전년도매출(손생)`,
      useNlLifeUnifiedYAxis: false,
      trimAfterLast: true,
    });

    renderCompareLineChart({
      canvasId: "carDailyCumsumChart",
      warnId: "carChartWarn",
      chartKey: "__carDailyCumsumChart",
      thisMonthScriptId: "car-chart-cumsum",
      prevMonthScriptId: "prev-car-chart-cumsum",
      yearAgoScriptId: "py-car-chart-cumsum",   
      thisLabel: "당월매출(자동차)",
      prevLabel: `전월매출(자동차)`,
      yearAgoLabel: `전년도매출(자동차)`,
      useNlLifeUnifiedYAxis: false,
      trimAfterLast: true,
    });

    renderCompareLineChart({
      canvasId: "nonlifeDailyCumsumChart",
      warnId: "nonlifeChartWarn",
      chartKey: "__nonlifeDailyCumsumChart",
      thisMonthScriptId: "nonlife-chart-cumsum",
      prevMonthScriptId: "prev-nonlife-chart-cumsum",
      yearAgoScriptId: "py-nonlife-chart-cumsum",  
      thisLabel: "당월매출(손보)",
      prevLabel: `전월매출(손보)`,
      yearAgoLabel: `전년도매출(손보)`,
      useNlLifeUnifiedYAxis: true, // ✅ 손보/생보만 y축 통일
      trimAfterLast: true,
    });

    renderCompareLineChart({
      canvasId: "lifeDailyCumsumChart",
      warnId: "lifeChartWarn",
      chartKey: "__lifeDailyCumsumChart",
      thisMonthScriptId: "life-chart-cumsum",
      prevMonthScriptId: "prev-life-chart-cumsum",
      yearAgoScriptId: "py-life-chart-cumsum",  
      thisLabel: "당월매출(생보)",
      prevLabel: `전월매출(생보)`,
      yearAgoLabel: `전년도매출(생보)`,
      useNlLifeUnifiedYAxis: true, // ✅ 손보/생보만 y축 통일
      trimAfterLast: true,
    });
  }

  // =========================================================
  // Page size selector
  // =========================================================
  function initPageSize() {
    const sel = document.getElementById("pageSizeSelect");
    if (!sel) return;

    sel.addEventListener("change", function () {
      const v = (sel.value || "50").trim();
      const url = new URL(window.location.href);
      url.searchParams.set("page_size", v);
      url.searchParams.set("page", "1");
      window.location.href = url.toString();
    });
  }

  // =========================================================
  // Boot
  // =========================================================
  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("dash-sales");
    const ver = getStaticVer();
    try {
      console.log("[dash_sales_page] loaded v=" + ver);
    } catch (e) {}

    initPartBranchSync(root);
    initLifeNlInsurerSync(root);
    initCharts();
    initPageSize();
  });
})();
