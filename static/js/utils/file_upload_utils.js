/**
 * file_upload_utils.js (FINAL)
 * ---------------------------------------------------------
 * ✅ 전역 범용 파일 업로드 유틸리티
 * - 파일 추가/삭제, 용량 제한, FormData 전송, 기존 첨부 삭제 처리
 * - 인라인 style 0개 (CSS 클래스로 제어)
 * - 재사용성 강화: 기존 첨부 영역 selector 옵션화
 * - CSRF 보강: X-CSRFToken 헤더 자동 세팅
 *
 * 사용법:
 *   initFileUpload({
 *     formSelector: "#postForm",
 *     fileInputSelector: "#fileInput",
 *     fileListSelector: "#fileNames",
 *     noFilesTextSelector: "#noFilesText",
 *     deleteContainerSelector: "#deleteContainer",
 *     existingFileSelector: ".remove-existing",
 *
 *     // ✅ 옵션화 (기존 첨부 영역이 페이지마다 다를 수 있음)
 *     existingFilesSelector: "#existingFiles",
 *     existingFileListWrapSelector: "#existingFileList",
 *     existingEmptyHtml: '<p class="text-muted small m-0">첨부된 파일이 없습니다.</p>',
 *
 *     // ✅ UI classes (인라인 style 제거)
 *     fileNameMaxWidthClass: "file-name-80", // CSS에서 max-width 설정
 *
 *     maxFileSize: 10 * 1024 * 1024, // 10MB
 *   });
 *
 * ⚠️ CSS 필요(예: apps/board.css):
 *   .file-name-80 { max-width: 80%; }
 */

(function () {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function str(v) {
    return String(v == null ? "" : v).trim();
  }

  function getCookie(name) {
    var value = "; " + (document.cookie || "");
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function getCSRFToken(form) {
    // 1) form 내부 hidden input 우선
    var input = form ? qs('input[name="csrfmiddlewaretoken"]', form) : null;
    var fromInput = str(input && input.value);
    if (fromInput) return fromInput;

    // 2) 문서 내 전역 csrf input
    var any = qs('input[name="csrfmiddlewaretoken"]');
    var fromDoc = str(any && any.value);
    if (fromDoc) return fromDoc;

    // 3) cookie fallback
    return str(getCookie("csrftoken"));
  }

  function buildHeaders(csrf) {
    var h = {};
    // FormData 사용 시 Content-Type을 직접 지정하지 않는게 안전
    if (csrf) {
      h["X-CSRFToken"] = csrf;
    }
    h["X-Requested-With"] = "XMLHttpRequest";
    return h;
  }

  function formatFileSize(bytes) {
    if (!bytes) return "0 B";
    var units = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(1024));
    var size = bytes / Math.pow(1024, i);
    return size.toFixed(1) + " " + units[i];
  }

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

        // 기존 첨부 삭제 버튼 selector
        existingFileSelector: ".remove-existing",

        // ✅ 기존 첨부 영역 옵션화
        existingFilesSelector: "#existingFiles", // li들이 들어있는 컨테이너
        existingFileListWrapSelector: "#existingFileList", // empty message를 넣을 wrapper
        existingEmptyHtml: '<p class="text-muted small m-0">첨부된 파일이 없습니다.</p>',

        // ✅ 인라인 style 제거용 클래스
        fileNameMaxWidthClass: "file-name-80",

        // size limit
        maxFileSize: 10 * 1024 * 1024, // 10MB

        // submit callbacks
        onSubmitSuccess: null, // function(redirectUrl){}
        onSubmitError: null, // function(htmlText){}
      },
      options || {}
    );

    // ---------------------------------------------
    // 📋 주요 DOM 요소
    // ---------------------------------------------
    var form = qs(config.formSelector);
    var fileInput = qs(config.fileInputSelector);
    var fileList = qs(config.fileListSelector);
    var noFilesText = qs(config.noFilesTextSelector);
    var deleteContainer = qs(config.deleteContainerSelector);

    if (!form || !fileInput) {
      console.warn("⚠️ initFileUpload: 필수 요소가 없습니다.", {
        form: !!form,
        fileInput: !!fileInput,
      });
      return;
    }

    // deleteContainer가 없으면 form에 붙임(방어)
    if (!deleteContainer) deleteContainer = form;

    // 선택된 파일(신규 첨부)
    var selectedFiles = [];

    // ---------------------------------------------
    // 🗑️ 기존 첨부파일 삭제 (수정 페이지)
    // ---------------------------------------------
    var existingButtons = qsa(config.existingFileSelector);
    existingButtons.forEach(function (btn) {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", function () {
        var fileId = str(btn.dataset.id);
        if (!fileId) return;

        var li = btn.closest ? btn.closest("li") : null;

        // delete_files hidden input 추가
        var hiddenInput = document.createElement("input");
        hiddenInput.type = "hidden";
        hiddenInput.name = "delete_files";
        hiddenInput.value = fileId;
        deleteContainer.appendChild(hiddenInput);

        if (li && li.remove) li.remove();

        // 남은 기존 파일이 없으면 empty message 표시
        var existingList = qs(config.existingFilesSelector);
        var wrap = qs(config.existingFileListWrapSelector);
        if (existingList && wrap) {
          var remaining = qsa("li", existingList).length;
          if (remaining === 0) {
            wrap.innerHTML = config.existingEmptyHtml;
          }
        }
      });
    });

    // ---------------------------------------------
    // 📎 새 파일 추가
    // ---------------------------------------------
    if (fileInput.dataset.bound !== "1") {
      fileInput.dataset.bound = "1";

      fileInput.addEventListener("change", function (event) {
        var files = event && event.target ? event.target.files : null;
        var newFiles = files ? Array.prototype.slice.call(files) : [];

        newFiles.forEach(function (file) {
          if (!file) return;

          if (file.size > config.maxFileSize) {
            alert(
              "⚠️ " +
                file.name +
                "은(는) " +
                (config.maxFileSize / (1024 * 1024)).toFixed(0) +
                "MB를 초과합니다."
            );
            return;
          }
          selectedFiles.push(file);
        });

        updateFileList();
        fileInput.value = ""; // 동일 파일 재선택 가능
      });
    }

    // ---------------------------------------------
    // 📦 파일 목록 갱신
    // ---------------------------------------------
    function updateFileList() {
      if (!fileList) return;

      fileList.innerHTML = "";

      if (!selectedFiles.length) {
        if (noFilesText) noFilesText.style.display = "block"; // (기존 UI 유지) *inline style 아닌 display 토글은 괜찮음
        return;
      }
      if (noFilesText) noFilesText.style.display = "none";

      selectedFiles.forEach(function (file, index) {
        var li = document.createElement("li");
        li.className =
          "d-flex justify-content-between align-items-center py-1 border-bottom";

        var nameSpan = document.createElement("span");
        nameSpan.textContent = file.name + " (" + formatFileSize(file.size) + ")";
        nameSpan.className =
          "small text-dark text-truncate " + str(config.fileNameMaxWidthClass);

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
    // 🚀 FormData 전송 (CSRF 보강)
    // ---------------------------------------------
    if (form.dataset.boundUpload !== "1") {
      form.dataset.boundUpload = "1";

      form.addEventListener("submit", function (e) {
        e.preventDefault();

        var formData = new FormData(form);

        // selectedFiles를 attachments로 append
        selectedFiles.forEach(function (file) {
          formData.append("attachments", file);
        });

        var csrf = getCSRFToken(form);
        var headers = buildHeaders(csrf);

        fetch(form.action || window.location.href, {
          method: "POST",
          body: formData,
          headers: headers,
          credentials: "same-origin",
        })
          .then(function (response) {
            // Django: 성공 시 redirect 흔함
            if (response.redirected) {
              if (typeof config.onSubmitSuccess === "function") {
                config.onSubmitSuccess(response.url);
              } else {
                window.location.href = response.url;
              }
              return null;
            }

            // redirect가 아니면 HTML(폼 에러)일 가능성
            return response.text().then(function (html) {
              if (typeof config.onSubmitError === "function") {
                config.onSubmitError(html);
              } else {
                document.body.innerHTML = html;
              }
              return null;
            });
          })
          .catch(function (err) {
            alert("파일 업로드 중 오류가 발생했습니다.");
            console.error(err);
          });
      });
    }

    // 초기 상태 반영
    updateFileList();
  };
})();
