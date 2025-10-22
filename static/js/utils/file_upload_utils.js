/**
 * file_upload_utils.js
 * 전역 범용 파일 업로드 유틸리티 (Render 호환 ES5 버전)
 * - 파일 추가 / 삭제 / 용량 제한 / FormData 전송
 * - post_create, post_edit 등 모든 업로드 페이지에서 재사용 가능
 *
 * 사용법:
 *   initFileUpload({
 *     formSelector: "#postForm",
 *     maxFileSize: 10 * 1024 * 1024,
 *     existingFileSelector: ".remove-existing",     // (선택)
 *     deleteContainerSelector: "#deleteContainer",  // (선택)
 *   });
 */

window.initFileUpload = function (options) {
  // ---------------------------------------------
  // ⚙️ 옵션 병합
  // ---------------------------------------------
  var config = Object.assign(
    {
      formSelector: "#postForm",
      fileInputSelector: "#fileInput",
      fileListSelector: "#fileNames",
      noFilesTextSelector: "#noFilesText",
      deleteContainerSelector: "#deleteContainer",
      existingFileSelector: ".remove-existing",
      maxFileSize: 10 * 1024 * 1024, // 10MB
      onSubmitSuccess: null,
      onSubmitError: null,
    },
    options || {}
  );

  // ---------------------------------------------
  // 📋 주요 DOM 요소
  // ---------------------------------------------
  var form = document.querySelector(config.formSelector);
  var fileInput = document.querySelector(config.fileInputSelector);
  var fileList = document.querySelector(config.fileListSelector);
  var noFilesText = document.querySelector(config.noFilesTextSelector);
  var deleteContainer = document.querySelector(config.deleteContainerSelector);

  var selectedFiles = [];

  if (!form || !fileInput) {
    console.warn("⚠️ initFileUpload: 필수 요소가 없습니다.");
    return;
  }

  // ---------------------------------------------
  // 🗑️ 기존 첨부파일 삭제 (수정 페이지)
  // ---------------------------------------------
  var existingButtons = document.querySelectorAll(config.existingFileSelector);
  existingButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var fileId = btn.dataset.id;
      var li = btn.closest("li");

      var hiddenInput = document.createElement("input");
      hiddenInput.type = "hidden";
      hiddenInput.name = "delete_files";
      hiddenInput.value = fileId;
      deleteContainer.appendChild(hiddenInput);

      li.remove();

      var remaining = document.querySelectorAll("#existingFiles li").length;
      if (remaining === 0) {
        document.getElementById("existingFileList").innerHTML =
          '<p class="text-muted small m-0">첨부된 파일이 없습니다.</p>';
      }
    });
  });

  // ---------------------------------------------
  // 📎 새 파일 추가
  // ---------------------------------------------
  fileInput.addEventListener("change", function (event) {
    var newFiles = Array.prototype.slice.call(event.target.files);
    newFiles.forEach(function (file) {
      if (file.size > config.maxFileSize) {
        alert(
          "⚠️ " +
            file.name +
            "은(는) " +
            config.maxFileSize / (1024 * 1024) +
            "MB를 초과합니다."
        );
      } else {
        selectedFiles.push(file);
      }
    });
    updateFileList();
    fileInput.value = "";
  });

  // ---------------------------------------------
  // 📦 파일 목록 갱신
  // ---------------------------------------------
  function updateFileList() {
    fileList.innerHTML = "";

    if (selectedFiles.length === 0) {
      noFilesText.style.display = "block";
      return;
    }
    noFilesText.style.display = "none";

    selectedFiles.forEach(function (file, index) {
      var li = document.createElement("li");
      li.className =
        "d-flex justify-content-between align-items-center py-1 border-bottom";

      var nameSpan = document.createElement("span");
      nameSpan.textContent =
        file.name + " (" + formatFileSize(file.size) + ")";
      nameSpan.className = "small text-dark text-truncate";
      nameSpan.style.maxWidth = "80%";

      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "btn btn-sm btn-outline-danger";
      removeBtn.textContent = "✖";
      removeBtn.addEventListener("click", function () {
        selectedFiles.splice(index, 1);
        updateFileList();
      });

      li.appendChild(nameSpan);
      li.appendChild(removeBtn);
      fileList.appendChild(li);
    });
  }

  // ---------------------------------------------
  // 📏 파일 크기 포맷 함수
  // ---------------------------------------------
  function formatFileSize(bytes) {
    if (bytes === 0) return "0 B";
    var units = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + " " + units[i];
  }

  // ---------------------------------------------
  // 🚀 FormData 전송
  // ---------------------------------------------
  form.addEventListener("submit", function (e) {
    e.preventDefault();

    var formData = new FormData(form);
    selectedFiles.forEach(function (file) {
      formData.append("attachments", file);
    });

    fetch(form.action || window.location.href, {
      method: "POST",
      body: formData,
    })
      .then(function (response) {
        if (response.redirected) {
          if (config.onSubmitSuccess) config.onSubmitSuccess(response.url);
          else window.location.href = response.url;
        } else {
          response.text().then(function (html) {
            if (config.onSubmitError) config.onSubmitError(html);
            else document.body.innerHTML = html;
          });
        }
      })
      .catch(function (err) {
        alert("파일 업로드 중 오류가 발생했습니다.");
        console.error(err);
      });
  });
};
