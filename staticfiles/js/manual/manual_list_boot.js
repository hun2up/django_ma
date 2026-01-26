// django_ma/static/js/manual/manual_list_boot.js
// ============================================================================
// Manual List Boot
// - template dataset → window.ManualListBoot
// ============================================================================

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
