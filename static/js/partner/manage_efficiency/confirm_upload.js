// django_ma/static/js/partner/manage_efficiency/confirm_upload.js
import { els } from "./dom_refs.js";
import { alertBox, getCSRFToken, selectedYM, showLoading, hideLoading } from "./utils.js";

function str(v) { return String(v ?? "").trim(); }

function getRoot() {
  return els.root || document.getElementById("manage-efficiency");
}

function getUploadUrl(root) {
  // ✅ 템플릿 root dataset에 이미 있는 값 사용
  return (
    root?.dataset?.efficiencyConfirmUploadUrl ||
    root?.dataset?.dataEfficiencyConfirmUploadUrl || // 혹시 다른 키로 내려왔을 때 대비
    "/partner/efficiency/upload-confirm/"
  );
}

function getBranchValue() {
  // superuser면 branchSelect가 있고, 그 외에는 currentUser.branch
  return (
    str(document.getElementById("branchSelect")?.value) ||
    str(window.currentUser?.branch) ||
    str(getRoot()?.dataset?.branch) ||
    ""
  );
}

function getPartValue() {
  return (
    str(window.currentUser?.part) ||
    str(getRoot()?.dataset?.part) ||
    ""
  );
}

export function initConfirmUploadHandlers() {
  const root = getRoot();
  if (!root) return;

  const btnDo = document.getElementById("btnConfirmUploadDo");
  const fileInput = document.getElementById("confirmFileInput");
  const fileNameBox = document.getElementById("confirmFileName"); // 업로드 된 파일명 표시 input(있다면)

  if (!btnDo || !fileInput) return;

  // ✅ 중복 바인딩 방지
  if (btnDo.dataset.bound === "1") return;
  btnDo.dataset.bound = "1";

  btnDo.addEventListener("click", async () => {
    const f = fileInput.files?.[0];
    if (!f) {
      alertBox("파일을 선택해주세요.");
      return;
    }

    const month = selectedYM(els.year, els.month); // "YYYY-MM"
    const branch = getBranchValue();
    const part = getPartValue();

    if (!month) {
      alertBox("연/월 선택을 확인해주세요.");
      return;
    }
    if (!branch) {
      alertBox("지점 정보를 찾을 수 없습니다.");
      return;
    }

    const url = getUploadUrl(root);

    const fd = new FormData();
    fd.append("file", f);
    fd.append("month", month);
    fd.append("branch", branch);
    fd.append("part", part);

    btnDo.disabled = true;
    showLoading("업로드 중...");

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCSRFToken(),
          // ⚠️ FormData는 Content-Type 지정하지 마세요 (브라우저가 boundary를 붙임)
        },
        body: fd,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.status !== "success") {
        alertBox(data.message || `업로드 실패 (${res.status})`);
        return;
      }

      // ✅ attachment_id를 저장용으로 보관 (save 때 payload에 넣기 위함)
      root.dataset.confirmAttachmentId = String(data.attachment_id || "");

      // ✅ 화면에 파일명 표시(있으면)
      if (fileNameBox) fileNameBox.value = data.file_name || f.name;

      alertBox("✅ 확인서 업로드 완료");
    } catch (e) {
      console.error("confirm upload error:", e);
      alertBox("업로드 중 오류가 발생했습니다.");
    } finally {
      hideLoading();
      btnDo.disabled = false;
    }
  });
}
