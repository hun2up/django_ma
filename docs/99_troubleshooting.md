# django_ma/docs/99_troubleshooting.md

# 트러블슈팅 가이드

## 1. 엑셀 업로드가 0%에서 멈춤
- Redis 연결 확인
- Celery worker 실행 여부 확인
- 업로드 작업이 Queue에 쌓였는지 점검

---

## 2. 검색 결과가 안 나오는 경우
- accounts/search_api.py 정책 확인
- grade / scope / branch 점검
- 공통 모달(search_user_modal)에서 search_url이 올바른지 확인

---

## 3. 로그인 안 되는 사용자
- grade == inactive 여부 확인
- CustomUser.is_active 값 확인
- 인증 백엔드/세션 문제 여부 점검

---

## 4. 매뉴얼은 보이는데 들어가면 권한 오류
- 목록 노출과 상세 접근 권한은 다를 수 있음
- manual_accessible_or_denied 로직 확인
- admin_only / is_published / grade 점검

---

## 5. 운영 DB 연결 차단 오류
- DEBUG=True 상태에서 운영 DB 연결 시도 여부 확인
- 환경변수(APP_ENV) 및 DB host 설정 점검

---

## 6. [board] 첨부파일 다운로드가 404/403 또는 파일이 열리지 않음
- 템플릿에서 `att.file.url`을 사용하지 않았는지 확인(금지)
- 반드시 다운로드 뷰 URL을 사용해야 함
  - Post: `board:post_attachment_download`
  - Task: `board:task_attachment_download`
- 권한 검증 로직(attachments view/service)에서 현재 사용자 접근 허용인지 확인

---

## 7. [board] 목록/상세에서 담당자/상태 변경이 저장되지 않음
- Boot div의 `data-update-url`가 존재하는지 확인
  - post_list: `#postListBoot[data-update-url]`
  - post_detail: `#postDetailBoot[data-update-url]`
  - task_list: `#taskListBoot[data-update-url]`
  - task_detail: `#taskDetailBoot[data-update-url]`
- CSRF 토큰이 요청 헤더/폼에서 정상 전달되는지 확인
- superuser가 아닌데 인라인 업데이트가 동작하려는 구조인지 점검
  - JS는 updateUrl 없으면 자동 종료하도록 설계(정상)

---

## 8. [board] 댓글 인라인 수정이 동작하지 않음
- `#commentEditCsrfToken` hidden input이 detail 템플릿에 존재하는지 확인
- `static/js/board/common/comment_edit.js` 로드 여부 확인
- 댓글 리스트 템플릿 구조(.comment-content[data-comment-id], p.comment-text 등)가 기준과 일치하는지 점검

---

## 9. [board] 모바일에서 업무요청서/소명서 입력폼이 깨짐
- `apps/board.css`가 로드되는지 확인(board/base_board.html 상속 여부)
- support_form: `.support-user-scroll` 및 `#support-form .user-row` 정책 확인
- states_form/support_form 템플릿에서 row에 인라인 style이 남아있는지 점검(가능하면 제거)
