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
    } catch (e) {
      // ignore
    }
    window[chartKey] = null;
  }

  function renderLineChart(opts) {
    const {
      canvasId,
      warnId,
      labelsScriptId,
      dataScriptId,
      chartKey,
      datasetLabel,
      emptyMessage,
      chartMissingMessage,
    } = opts;

    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const labels = safeJsonFromScriptTag(labelsScriptId, []);
    const cumsum = safeJsonFromScriptTag(dataScriptId, []);

    if (!Array.isArray(labels) || !Array.isArray(cumsum) || labels.length === 0 || cumsum.length === 0) {
      showWarnById(warnId, emptyMessage || "차트 데이터가 없습니다.");
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

    const ctx = canvas.getContext("2d");
    window[chartKey] = new window.Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: datasetLabel || "누적 영수금",
            data: cumsum,
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
        scales: {
          y: {
            ticks: {
              callback: (v) => Number(v).toLocaleString(),
            },
          },
        },
      },
    });
  }

  function initCharts() {
    // (좌) 손생 장기매출 (자동차/일시납 제외된 데이터)
    renderLineChart({
      canvasId: "dailyCumsumChart",
      warnId: "chartWarn",
      labelsScriptId: "chart-labels",
      dataScriptId: "chart-cumsum",
      chartKey: "__dailyCumsumChart",
      datasetLabel: "누적 영수금(손생)",
      emptyMessage: "차트 데이터가 없습니다. (영수일자/영수금이 비어있거나 필터 결과가 없습니다)",
    });

    // (우) 자동차 매출 (life_nl='자동차'만)
    renderLineChart({
      canvasId: "carDailyCumsumChart",
      warnId: "carChartWarn",
      labelsScriptId: "car-chart-labels",
      dataScriptId: "car-chart-cumsum",
      chartKey: "__carDailyCumsumChart",
      datasetLabel: "누적 영수금(자동차)",
      emptyMessage: "차트 데이터가 없습니다. (자동차 영수 데이터가 없거나 필터 결과가 없습니다)",
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
    initCharts();
    initPageSize();
  });
})();
