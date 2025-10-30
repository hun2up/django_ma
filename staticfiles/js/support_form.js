/**
 * django_ma/static/js/support_form.js
 * 업무요청서 페이지 전용 스크립트
 * 기능: 행 추가/삭제, 사용자 검색, PDF 생성
 */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("requestForm");
  const overlay = document.getElementById("loadingOverlay");
  const generateBtn = document.getElementById("generatePdfBtn");

  /** -------------------------------
   * ✅ 공통 행 제어 유틸 함수
   * ------------------------------- */
  const handleRowControl = (rowSelector, addBtnId, resetBtnId, removeBtnClass, maxCount, alertMsg) => {
    const rows = document.querySelectorAll(rowSelector);
    const addBtn = document.getElementById(addBtnId);
    const resetBtn = document.getElementById(resetBtnId);

    // ➕ 행 추가
    addBtn.addEventListener("click", () => {
      const hidden = Array.from(rows).filter(r => r.style.display === "none");
      if (!hidden.length) return alert(alertMsg);
      hidden[0].style.display = "";
    });

    // ♻️ 초기화
    resetBtn.addEventListener("click", () => {
      document.querySelectorAll(`${rowSelector} input`).forEach(el => (el.value = ""));
      rows.forEach((r, i) => {
        if (i > 0) r.style.display = "none";
      });
    });

    // ❌ 행 제거
    document.querySelectorAll(`.${removeBtnClass}`).forEach(btn => {
      btn.addEventListener("click", () => {
        const row = document.querySelector(`${rowSelector}[data-index="${btn.dataset.index}"]`);
        if (row) {
          row.querySelectorAll("input").forEach(el => (el.value = ""));
          row.style.display = "none";
        }
      });
    });
  };

  // 요청대상 / 계약사항 공통 적용
  handleRowControl(".user-row", "addUserBtn", "resetUserBtn", "btn-remove", 5, "요청대상은 최대 5개까지만 입력 가능합니다. \n추가 입력이 필요한 경우 상세내용 칸에 기재해주세요.");
  handleRowControl(".contract-row", "addContractBtn", "resetContractBtn", "btn-remove", 5, "계약사항은 최대 5개까지만 입력 가능합니다. \n추가 입력이 필요한 경우 상세내용 칸에 기재해주세요.");


  /** -------------------------------
   * 🔍 대상자 검색
   * ------------------------------- */
  document.querySelectorAll('.btn-open-search').forEach(btn => {
    btn.addEventListener('click', () => (currentRow = btn.dataset.row));
  });

  // ✅ 공통 모달에서 userSelected 이벤트 수신
  document.addEventListener("userSelected", (e) => {
    const u = e.detail;
    if (!currentRow) return;
    document.querySelector(`input[name="target_name_${currentRow}"]`).value = u.name;
    document.querySelector(`input[name="target_code_${currentRow}"]`).value = u.id;
    document.querySelector(`input[name="target_join_${currentRow}"]`).value = u.enter;
    document.querySelector(`input[name="target_leave_${currentRow}"]`).value = u.quit;
  });

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

  /** -------------------------------
   * 🧾 PDF 생성 요청
   * ------------------------------- */
  generateBtn.addEventListener("click", async () => {
    overlay.style.display = "block";

    try {
      const formData = new FormData(form);

      // ✅ URL은 HTML에서 data 속성으로 가져옴
      const pdfUrl = generateBtn.dataset.pdfUrl;

      const response = await fetch(pdfUrl, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value },
      });

      if (!response.ok) throw new Error("PDF 생성 실패");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "업무요청서.pdf";
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
