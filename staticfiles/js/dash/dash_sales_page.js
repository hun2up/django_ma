// static/js/dash/dash_sales_page.js
(function () {
  "use strict";

  // -----------------------------
  // JSON helpers
  // -----------------------------
  function safeJsonFromScriptTag(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent || "");
    } catch (e) {
      return fallback;
    }
  }

  // -----------------------------
  // Part -> Branch sync
  // -----------------------------
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

  // -----------------------------
  // Life_nl -> Insurer sync (즉시 연동)
  // -----------------------------
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
        const all = []
          .concat(map["손보"] || [], map["생보"] || [], map["자동차"] || []);
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

    // 손생 변경 시: 보험사는 전체로 리셋 + 즉시 옵션 교체
    lifeEl.addEventListener("change", function () {
      insurerEl.value = "";
      syncInsurers("");
    });
  }

  // -----------------------------
  // Chart helpers
  // -----------------------------
  function showWarnById(warnId, msg) {
    const warnEl = document.getElementById(warnId);
    if (!warnEl) return;
    warnEl.style.display = "block";
    warnEl.textContent = msg;
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
    // input: ["2026-01-01", ...]
    // output: ["1", "2", ...]
    return (dateLabels || []).map((s) => {
      const m = String(s || "").match(/-(\d{2})$/);
      if (!m) return s;
      const d = parseInt(m[1], 10);
      return String(d);
    });
  }

  function renderLineChart(opts) {
    const {
      canvasId,
      warnId,
      dataScriptId,
      chartKey,
      datasetLabel,
      emptyMessage,
      chartMissingMessage,
      useNlLifeUnifiedYAxis,
    } = opts;

    const hasAnyValue = data.some((v) => Number(v || 0) !== 0);

    // 0뿐인 달이어도 차트는 그린다(경고는 선택)
    if (!hasAnyValue) {
    // 필요하면 한 줄 안내만 (원치 않으면 이 블록 통째로 삭제)
    showWarnById(warnId, "해당 월은 누적값이 0입니다.");
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // ✅ 공통 라벨 (YYYY-MM-DD) -> 표시용(1~말일)
    const rawLabels = safeJsonFromScriptTag("chart-day-labels", []);
    const labels = toDayOfMonthLabels(rawLabels);

    const data = safeJsonFromScriptTag(dataScriptId, []);

    if (!Array.isArray(labels) || labels.length === 0) {
      showWarnById(warnId, "차트 라벨(월 1~말일)이 없습니다.");
      return;
    }
    if (!Array.isArray(data) || data.length !== labels.length) {
      showWarnById(warnId, "차트 데이터 길이가 라벨과 일치하지 않습니다.");
      return;
    }

    if (typeof window.Chart === "undefined") {
      showWarnById(
        warnId,
        chartMissingMessage || "Chart.js 로드에 실패했습니다. (정적 파일 경로/collectstatic 여부 확인)"
      );
      return;
    }

    destroyChart(chartKey);

    const nlStep = safeJsonFromScriptTag("nl-l-y-step", null);
    const nlMax = safeJsonFromScriptTag("nl-l-y-max", null);

    const yScale = {
      ticks: { callback: (v) => Number(v).toLocaleString() },
    };

    // ✅ 손보/생보 2개만 y축 눈금 통일
    if (useNlLifeUnifiedYAxis && typeof nlStep === "number" && typeof nlMax === "number") {
      yScale.beginAtZero = true;
      yScale.suggestedMax = nlMax;
      yScale.ticks = {
        stepSize: nlStep,
        callback: (v) => Number(v).toLocaleString(),
      };
    }

    const ctx = canvas.getContext("2d");
    window[chartKey] = new window.Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: datasetLabel || "누적 영수금",
            data,
            tension: 0.25,
            pointRadius: 2,
            borderWidth: 2,
          },
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
                const v = (ctx && ctx.parsed && typeof ctx.parsed.y !== "undefined") ? ctx.parsed.y : 0;
                const label = datasetLabel || "누적 영수금";
                return label + ": " + Number(v || 0).toLocaleString();
              },
            },
          },
        },
        scales: { y: yScale },
      },
    });
  }

  function initCharts() {
    renderLineChart({
      canvasId: "dailyCumsumChart",
      warnId: "chartWarn",
      dataScriptId: "chart-cumsum",
      chartKey: "__dailyCumsumChart",
      datasetLabel: "누적 영수금(손생)",
      emptyMessage: "차트 데이터가 없습니다.",
      useNlLifeUnifiedYAxis: false, // ✅ 제외
    });

    renderLineChart({
      canvasId: "carDailyCumsumChart",
      warnId: "carChartWarn",
      dataScriptId: "car-chart-cumsum",
      chartKey: "__carDailyCumsumChart",
      datasetLabel: "누적 영수금(자동차)",
      emptyMessage: "차트 데이터가 없습니다.",
      useNlLifeUnifiedYAxis: false, // ✅ 제외
    });

    renderLineChart({
      canvasId: "nonlifeDailyCumsumChart",
      warnId: "nonlifeChartWarn",
      dataScriptId: "nonlife-chart-cumsum",
      chartKey: "__nonlifeDailyCumsumChart",
      datasetLabel: "누적 영수금(손보)",
      emptyMessage: "차트 데이터가 없습니다.",
      useNlLifeUnifiedYAxis: true, // ✅ 손보/생보만 통일
    });

    renderLineChart({
      canvasId: "lifeDailyCumsumChart",
      warnId: "lifeChartWarn",
      dataScriptId: "life-chart-cumsum",
      chartKey: "__lifeDailyCumsumChart",
      datasetLabel: "누적 영수금(생보)",
      emptyMessage: "차트 데이터가 없습니다.",
      useNlLifeUnifiedYAxis: true, // ✅ 손보/생보만 통일
    });
  }

  // -----------------------------
  // Page size selector
  // -----------------------------
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

  // -----------------------------
  // Boot
  // -----------------------------
  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("dash-sales");
    initPartBranchSync(root);
    initLifeNlInsurerSync(root);
    initCharts();
    initPageSize();
  });
})();
