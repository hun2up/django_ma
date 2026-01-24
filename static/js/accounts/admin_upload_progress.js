/**
 * accounts/admin_upload_progress.js
 *
 * Admin - CustomUser Excel upload progress polling
 *
 * Template contract:
 *  - #uploadProgressBox must exist
 *  - data-task-id="..." : celery task id
 *  - data-progress-url="..." : polling endpoint (JSON)
 *
 * DOM contract:
 *  - #progressBar
 *  - #progressStatusText
 *  - #progressErrorText
 *  - #resultDownloadBtn
 *
 * Response contract (JSON):
 *  - percent: number (0~100)
 *  - status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILURE"
 *  - error: string
 *  - download_url: string (present on SUCCESS)
 */
(function () {
  // Prevent duplicate execution (BFCache / admin navigation quirks)
  if (window.__accountsUsersUploadPollingStarted) return;
  window.__accountsUsersUploadPollingStarted = true;

  const box = document.getElementById("uploadProgressBox");
  if (!box) return;

  const taskId = (box.dataset.taskId || "").trim();
  const progressUrl = (box.dataset.progressUrl || "").trim();
  if (!taskId || !progressUrl) return;

  const barEl = document.getElementById("progressBar");
  const statusEl = document.getElementById("progressStatusText");
  const errorEl = document.getElementById("progressErrorText");
  const downloadBtn = document.getElementById("resultDownloadBtn");

  // Defensive: required nodes
  if (!barEl || !statusEl || !errorEl || !downloadBtn) return;

  const POLL_INTERVAL_MS = 1000;
  const ERROR_RETRY_MS = 3000;

  function clampPercent(v) {
    const n = Number(v || 0);
    if (Number.isNaN(n)) return 0;
    return Math.max(0, Math.min(100, n));
  }

  function setProgress(percent) {
    const p = clampPercent(percent);
    barEl.style.width = p + "%";
    barEl.textContent = p + "%";
  }

  function setStatus(text) {
    statusEl.textContent = text || "";
  }

  function setError(text) {
    errorEl.textContent = text || "";
  }

  function enableDownload(url) {
    downloadBtn.href = url;
    downloadBtn.classList.remove("disabled");
    downloadBtn.setAttribute("aria-disabled", "false");
  }

  async function poll() {
    try {
      const url = progressUrl + "?task_id=" + encodeURIComponent(taskId);
      const res = await fetch(url, { cache: "no-store" });

      // If server returned non-200 or HTML, fail gracefully
      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }

      const data = await res.json();

      const percent = clampPercent(data.percent);
      const status = String(data.status || "PENDING");
      const error = String(data.error || "");
      const downloadUrl = String(data.download_url || "");

      setProgress(percent);
      setStatus(status + " (" + percent + "%)");
      setError("");

      if (status === "FAILURE") {
        setError(error || "처리 실패");
        return; // stop polling
      }

      if (status === "SUCCESS") {
        if (downloadUrl) {
          enableDownload(downloadUrl);
          setStatus("완료!");
        } else {
          setError("완료되었지만 다운로드 링크를 찾지 못했습니다.");
        }
        return; // stop polling
      }

      setTimeout(poll, POLL_INTERVAL_MS);
    } catch (e) {
      setError("진행률 조회 오류");
      setTimeout(poll, ERROR_RETRY_MS);
    }
  }

  poll();
})();
