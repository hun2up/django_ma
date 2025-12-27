// django_ma/static/js/partner/manage_rate/table_dropdown.js
import { els } from "./dom_refs.js";

const tableCache = new Map();

export function clearTableCache(branch = "") {
  const b = String(branch || "").trim();
  if (b) tableCache.delete(b);
  else tableCache.clear();
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null; // 404 HTML 등
  }
}

/**
 * branch의 TableSetting 목록을 서버에서 가져옴
 * return: [{ table, rate }, ...]
 */
export async function fetchBranchTables(branch) {
  const b = String(branch || "").trim();
  if (!b) return [];

  if (tableCache.has(b)) return tableCache.get(b);

  // ✅ 무조건 dataset URL 사용 (하드코딩 금지)
  const base = String(els.root?.dataset?.tableFetchUrl || "").trim(); // manage_rate.html: data-table-fetch-url
  if (!base) {
    console.warn("[rate] data-table-fetch-url 누락");
    tableCache.set(b, []);
    return [];
  }

  const url = new URL(base, window.location.origin);
  url.searchParams.set("branch", b);

  const res = await fetch(url.toString(), {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  });

  const data = await safeJson(res);

  if (!res.ok || !data || data.status !== "success") {
    console.warn("[rate] 테이블 목록 조회 실패:", res.status, data);
    tableCache.set(b, []);
    return [];
  }

  const rows = Array.isArray(data.rows) ? data.rows : [];
  const tables = rows
    .map((r) => ({
      table: String(r.table || r.table_name || "").trim(),
      rate: String(r.rate ?? "").trim(),
    }))
    .filter((x) => x.table);

  tableCache.set(b, tables);
  return tables;
}

/**
 * after_ftable/after_ltable을 select로 교체하고
 * ✅ 옵션에는 "테이블명만" 표시
 * 선택시 after_frate/after_lrate 자동 입력
 */
export function applyTableDropdownToRow(rowEl, tables = []) {
  if (!rowEl) return;

  const makeSelect = (name) => {
    const existing = rowEl.querySelector(`select[name="${name}"]`);
    if (existing) return existing;

    const input = rowEl.querySelector(`input[name="${name}"]`);
    const keep = input?.value || "";

    const sel = document.createElement("select");
    sel.name = name;
    sel.className = "form-select form-select-sm";

    if (input && input.parentNode) input.parentNode.replaceChild(sel, input);
    else rowEl.appendChild(sel);

    if (keep) sel.value = keep;
    return sel;
  };

  const afterFSelect = makeSelect("after_ftable");
  const afterLSelect = makeSelect("after_ltable");

  // ✅ 옵션: 테이블명만
  const fillOptions = (sel) => {
    const current = sel.value || "";
    sel.innerHTML = `<option value="">선택</option>`;
    for (const t of tables) {
      const opt = document.createElement("option");
      opt.value = t.table;
      opt.textContent = t.table; // ⭐ 요율 표시 제거
      sel.appendChild(opt);
    }
    if (current) sel.value = current;
  };

  fillOptions(afterFSelect);
  fillOptions(afterLSelect);

  const rateMap = new Map(tables.map((t) => [t.table, t.rate]));
  const afterFRateInput = rowEl.querySelector(`[name="after_frate"]`);
  const afterLRateInput = rowEl.querySelector(`[name="after_lrate"]`);

  const syncRates = () => {
    if (afterFRateInput) afterFRateInput.value = rateMap.get(afterFSelect.value) || "";
    if (afterLRateInput) afterLRateInput.value = rateMap.get(afterLSelect.value) || "";
  };

  // onchange 덮어쓰기(중복 방지)
  afterFSelect.onchange = syncRates;
  afterLSelect.onchange = syncRates;

  syncRates();
}
