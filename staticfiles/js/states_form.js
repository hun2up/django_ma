/**
 * django_ma/static/js/states_form.js
 * FA 소명서 페이지 전용 스크립트
 * 기능: 계약사항 행 추가/삭제, PDF 생성
 */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("requestForm");
  const overlay = document.getElementById("loadingOverlay");
  const generateBtn = document.getElementById("generatePdfBtn");

  /** -------------------------------
   * ✅ 계약사항 행 제어 유틸
   * ------------------------------- */
  const handleRowControl = (rowSelector, addBtnId, resetBtnId, removeBtnClass, maxCount, alertMsg) => {
    const addBtn = document.getElementById(addBtnId);
    const resetBtn = document.getElementById(resetBtnId);

    addBtn.addEventListener("click", () => {
      const rows = document.querySelectorAll(rowSelector);
      const hidden = Array.from(rows).filter(r => r.style.display === "none");
      if (!hidden.length) return alert(alertMsg);
      hidden[0].style.display = "";
    });

    resetBtn.addEventListener("click", () => {
      const rows = document.querySelectorAll(rowSelector);
      rows.forEach((r, idx) => {
        if (idx === 0) r.style.display = "";
        else r.style.display = "none";
        r.querySelectorAll("input").forEach(input => (input.value = ""));
      });
    });

    document.addEventListener("click", e => {
      if (e.target.classList.contains(removeBtnClass)) {
        const row = e.target.closest(rowSelector);
        row.style.display = "none";
        row.querySelectorAll("input").forEach(input => (input.value = ""));
      }
    });
  };

    /** -------------------------------
   * 💰 보험료 입력칸 숫자만 허용 + 1,000단위 콤마
   * ------------------------------- */
  const premiumInputs = document.querySelectorAll('input[name^="premium_"]');
  premiumInputs.forEach(input => {
    input.addEventListener("input", e => {
      // 🔹 숫자 이외 문자 제거
      let value = e.target.value.replace(/[^0-9]/g, "");
      if (value) {
        // 🔹 1,000단위 콤마 추가
        value = Number(value).toLocaleString("ko-KR");
      }
      e.target.value = value;
    });

    // 🔹 복사/붙여넣기 시에도 숫자만 남게
    input.addEventListener("paste", e => {
      e.preventDefault();
      const paste = (e.clipboardData || window.clipboardData).getData("text");
      const clean = paste.replace(/[^0-9]/g, "");
      if (clean) e.target.value = Number(clean).toLocaleString("ko-KR");
    });
  });

  // 🔹 폼 전송 시 보험료 콤마 제거 (숫자만 서버로 전달)
  form.addEventListener("submit", () => {
    premiumInputs.forEach(input => {
      input.value = input.value.replace(/,/g, "");
    });
  });


  // ✅ 계약사항 제어만 활성화
  handleRowControl(".contract-row", "addContractBtn", "resetContractBtn", "btn-remove", 5, "계약사항은 최대 5개까지만 입력 가능합니다.");

    /** -------------------------------
   * 🧾 PDF 생성 요청
   * ------------------------------- */
  generateBtn.addEventListener("click", async () => {
    overlay.style.display = "flex";

    try {
      // ✅ FormData + CSRF Token 추가
      const formData = new FormData(form);
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      const pdfUrl = generateBtn.dataset.pdfUrl;

      const response = await fetch(pdfUrl, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": csrfToken },
      });

      if (!response.ok) throw new Error("PDF 생성 실패");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "FA_소명서.pdf";
      a.click();
      URL.revokeObjectURL(url);

    } catch (err) {
      alert("PDF 생성 중 오류가 발생했습니다.");
      console.error("❌ 오류:", err);
    } finally {
      overlay.style.display = "none";
    }
  });
});
