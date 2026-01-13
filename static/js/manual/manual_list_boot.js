// django_ma/static/js/manual/manual_list_boot.js
// --------------------------------------------------
// Manual List Boot Loader
// - 템플릿에서 내려준 dataset(URL) → window.ManualListBoot로 매핑
// - inline script 제거 목적
// --------------------------------------------------

(() => {
  const el = document.getElementById("manualListBoot");
  if (!el) return;

  const toStr = (v) => String(v ?? "").trim();

  window.ManualListBoot = {
    reorderUrl: toStr(el.dataset.reorderUrl),
    deleteUrl: toStr(el.dataset.deleteUrl),
    bulkUpdateUrl: toStr(el.dataset.bulkUpdateUrl),
  };
})();
