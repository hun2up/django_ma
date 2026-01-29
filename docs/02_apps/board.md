# django_ma/docs/02_apps/board.md

# Board 앱 가이드 (board.md)

## 1. Board 앱 개요

board 앱은 django_ma 내부 운영을 위한 **업무 처리 중심 앱**이다.  
단순 게시판이 아니라, 다음과 같은 역할을 수행한다.

- 업무요청(Post) 등록/처리/이력 관리
- 직원업무(Task) 내부 처리(superuser 전용)
- 댓글 기반 커뮤니케이션
- 첨부파일 업로드/보안 다운로드
- 상태/담당자 인라인 업데이트(AJAX)
- 업무요청서 / FA 소명서 PDF 출력

> ⚠️ **운영 시스템 앱**이므로  
> 보안(권한/첨부 다운로드)과 UX(인라인 처리)가 핵심 설계 포인트이다.

---

## 2. 디렉터리 구조 (최종 기준)

board/
├── models.py
├── urls.py
├── views/
│   ├── __init__.py              # re-export (단일 진입점)
│   ├── posts.py                 # Post CRUD + detail
│   ├── tasks.py                 # Task CRUD (superuser only)
│   ├── forms.py                 # support_form / states_form / PDF
│   └── attachments.py           # 첨부 다운로드 (보안 SSOT)
├── services/
│   ├── listing.py               # 목록 공용(검색/필터/페이지네이션)
│   ├── inline_update.py         # 상태/담당자 인라인 업데이트
│   ├── comments.py              # 댓글 공용(Post/Task)
│   └── attachments.py           # 첨부 저장/다운로드 로직
├── templates/
│   └── board/
│       ├── base_board.html
│       ├── post_list.html
│       ├── post_detail.html
│       ├── post_create.html
│       ├── post_edit.html
│       ├── task_list.html
│       ├── task_detail.html
│       ├── task_create.html
│       ├── task_edit.html
│       ├── support_form.html
│       ├── states_form.html
│       └── includes/
│           ├── _edit_form.html
│           ├── _form_common.html
│           ├── _comment_form.html
│           ├── _comment_list.html
│           ├── _inline_handler_status_list.html
│           └── pagination.html
└── static/
    ├── css/apps/board.css
    └── js/
        ├── common/
        │   └── forms/
        │       ├── dom.js
        │       ├── rows.js
        │       └── premium.js
        └── board/
            ├── states_form.js
            ├── support_form.js
            └── common/
                ├── status_ui.js
                ├── inline_update.js
                ├── detail_inline_update.js
                └── comment_edit.js
└── templatetags/
    ├── board_filters.py
    ├── querystring.py
    └── attachments.py

---

## 3. URL 구조

### 3-1. Post (업무요청)

| URL | 설명 | 
|-----|-----|
| /board/posts/ | 업무요청 목록 |
| /board/posts/create/ | 요청 등록 |
| /board/posts/<id>/ | 요청 상세 |
| /board/posts/<id>/edit/ | 요청 수정 |
| /board/posts/attachments/<att_id>/download/ | 첨부 다운로드 |

### 3-2. Task (직원업무, superuser 전용)

| URL | 설명 |
|-----|-----|
| /board/tasks/ | 직원업무 목록 |
| /board/tasks/create/ | 업무 등록 |
| /board/tasks/<id>/ | 업무 상세 |
| /board/tasks/<id>/edit/ | 업무 수정 |
| /board/tasks/attachments/<att_id>/download/ | 첨부 다운로드 |

### 3-3. 서식 / PDF

| URL | 설명 |
|-----|-----|
| /board/support-form/ | 업무요청서(PDF) |
| /board/states-form/	| FA 소명서(PDF) |
| /board/support-form/pdf/ | PDF 생성 API |
| /board/states-form/pdf/ | PDF 생성 API |

---

## 4. 템플릿 구조 및 상속 규칙

### 4-1. base_board.html (핵심)

{% extends "base.html" %}

{% block app_css %}
<link rel="stylesheet" href="{% static 'css/apps/board.css' %}">
{% endblock %}

{% block content_wrapper %}
<div class="board-scope">
  {{ block.super }}
</div>
{% endblock %}

### 핵심 규칙

- **모든 board 템플릿은 반드시 board/base_board.html 상속**
- .board-scope 외부로 CSS 누수 금지
- apps/board.css는 base.html에서 절대 직접 로드하지 않음

### 4-2. 대상 템플릿 목록

- post_list / post_detail / post_create / post_edit
- task_list / task_detail / task_create / task_edit
- support_form / states_form

> 전부 {% extends "board/base_board.html" %} 사용

---

## 5. JavaScript 구조 (공용 모듈)

### 5-1. status_ui.js

- 상태값 → 표준 CSS 클래스 매핑
- .status-select[data-status-ui="1"] 대상만 적용
- 인라인 업데이트 후 재적용 가능

### 5-2. inline_update.js (목록)

- 목록 페이지 상태/담당자 AJAX 업데이트
- CSRF 자동 처리
- 중복 요청 방지(busy 상태)

### 5-3. detail_inline_update.js (상세)

- 상세 페이지 인라인 업데이트
- 성공 시 상태 변경일 텍스트 갱신
- update URL 없으면 자동 종료(권한 방어)

### 5-4. comment_edit.js

- 댓글 인라인 수정/취소
- delegation 기반 바인딩
- CSRF 토큰 자동 탐색

## 5-5. forms 공통 유틸 (js/common/forms)

- dom.js
  - querySelector / show-hide 등 DOM 유틸
- rows.js
  - 행 추가/삭제/초기화 공통 패턴
- premium.js
  - 숫자 입력 + 콤마 포맷 처리
  - submit 시 숫자 정규화

> board 뿐 아니라 commission / partner 등
> 모든 “폼 중심 화면”에서 재사용 가능하도록 설계됨

---

## 6. CSS 설계 원칙 (board.css)

### 6-1. No-Leak Policy

- 모든 셀렉터는 .board-scope 하위
- textarea[name="content"] 등 위험 셀렉터도 스코프 내부 제한

### 6-2. 주요 스타일 범위

- 록 테이블 말줄임/nowrap 정책
- 댓글 UI (PC absolute / Mobile 하단)
- 첨부파일 UI
- 상태 배지/셀렉트 컬러링
- 모바일 서식 가로 스크롤(support_form)

---

## 7. 보안 설계 (중요)

### 7-1. 첨부파일 다운로드

❌ 금지:

<a href="{{ att.file.url }}">


✅ 허용:

<a href="{% url 'board:post_attachment_download' att.id %}">


- 모든 다운로드는 View를 경유
- 권한 검증 + 파일명 정규화 + RFC5987 적용

### 7-2. 권한 정책 요약

| 기능 | 접근 |
|-----|-----|
| Post | 로그인 사용자 |
| Task | superuser only |
| 인라인 업데이트 | superuser |
| support_form | superuser/head/leader |
| states_form | inactive 제외 |

---

## 8. 운영 포인트 / 주의사항

### 8-1. 절대 수정 시 주의

- services/attachments.py
- views/attachments.py
- base_board.html
- apps/board.css

> 잘못 수정 시 보안 사고 / CSS 전체 누수 발생 가능

### 8-2. 신규 기능 추가 시 권장 패턴

- 목록/검색 → services/listing.py 확장
- 상태/담당자 → services/inline_update.py 재사용
- 댓글 → services/comments.py 공용 사용
- CSS → 반드시 .board-scope 하위에만 작성

### 9. 요약

board 앱은 django_ma 내에서 가장 복합적이고 운영 의존도가 높은 앱이다.

- View는 얇게
- Service는 공용화
- CSS는 스코프 고립
- 첨부는 무조건 보안 경유
- 운영자 UX 최우선

👉 이 기준을 유지하면 장기 운영 / 인수인계 / 기능 확장 모두 안전하다.