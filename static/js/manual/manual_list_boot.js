// django_ma/static/js/manual/manual_list_boot.js
// -----------------------------------------------------------------------------
// Manual List Boot Loader (FINAL)
// - 템플릿 dataset(URL) -> window.ManualListBoot로 매핑
// -----------------------------------------------------------------------------

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
