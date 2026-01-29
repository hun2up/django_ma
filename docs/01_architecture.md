# django_ma/docs/01_architecture.md

# 프로젝트 아키텍처 (Architecture)

## 1. 전체 구조 개요
django_ma는 Django MVT 구조를 기반으로 하되,
운영 편의성과 유지보수를 위해 다음과 같은 계층 분리를 따른다.

[ Browser ]
↓
[ Django Template + Vanilla JS ]
↓
[ View / API Wrapper ]
↓
[ Service Layer (도메인 로직) ]
↓
[ Policy / Rule Layer (SSOT) ]
↓
[ Model ]
↓
[ PostgreSQL / Redis ]

---

## 2. accounts 앱 기준 아키텍처

accounts/
├── models.py              # CustomUser (SSOT)
├── search_api.py          # 사용자 검색 정책 (SSOT)
├── views.py               # HTTP wrapper / progress API
├── tasks.py               # Celery 비동기 업로드
├── admin.py               # 관리자 UI + 업로드 진입점
├── constants.py           # 공통 상수
├── decorators.py          # grade_required / inactive 차단
├── forms.py               # ExcelUploadForm, Auth 보강
├── services/
│   └── users_excel_import.py  # 엑셀 업로드 SSOT
├── signals.py             # CustomUser ↔ SubAdminTemp 동기화
├── utils.py               # affiliation_display 생성
├── urls.py
└── templates/admin/accounts/customuser/

---

## 3. manual 앱 기준 아키텍처
manual/
├── models.py              # Manual / Section / Block / Attachment
├── views/
│   ├── pages.py           # 화면 렌더링
│   ├── manual.py          # 매뉴얼 CRUD
│   ├── section.py         # 섹션 관리
│   ├── block.py           # 블록 관리
│   └── attachment.py      # 첨부 관리
├── utils/
│   ├── permissions.py     # 접근 정책
│   ├── rules.py           # 비즈니스 규칙
│   ├── serializers.py     # 프런트 직렬화
│   └── http.py            # JSON 응답
├── constants.py
└── urls.py

---

## 4. board 앱 기준 아키텍처 (리팩토링 완료)

### 4-1. 패키지 구조(권장/현행)
board/
├── models.py
├── urls.py
├── views/
│   ├── __init__.py              # re-export
│   ├── posts.py                 # Post list/detail/create/edit
│   ├── tasks.py                 # Task list/detail/create/edit (superuser only)
│   ├── forms.py                 # support_form / states_form / PDF endpoints
│   ├── attachments.py           # 첨부 다운로드(권한/보안 SSOT)
├── services/
│   ├── listing.py               # 목록 공용(필터/검색/페이지네이션)
│   ├── inline_update.py         # 인라인 업데이트 공용(handler/status)
│   ├── comments.py              # 댓글 공용(Post/Task)
│   └── attachments.py           # 첨부 저장/다운로드(open_fileresponse_*)
├── templates/board/
│   ├── base_board.html          # board 스코프 래퍼 + board.css 로드
│   ├── post_list/detail/create/edit.html
│   ├── task_list/detail/create/edit.html
│   ├── support_form.html        # 업무요청서 PDF
│   ├── states_form.html         # 소명서 PDF
│   └── includes/                # partials(_edit_form, _comment_*, pagination 등)
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

### 4-2. 핵심 설계 포인트
- View는 “화면/엔드포인트” 역할에 집중
- 서비스 레이어가 **공용 규칙**(목록/댓글/첨부/인라인업데이트)을 담당
- 첨부 다운로드는 보안 정책상 **FieldFile.url 직접 노출 금지**
- 템플릿은 include(partials)로 중복 최소화
- CSS는 board 스코프(`.board-scope`) 내부에서만 동작하도록 설계

---

## 5. 핵심 설계 포인트(프로젝트 공통)

### (1) 정책/규칙 중앙화(SSOT)
- 사용자 검색 정책: accounts/search_api.py
- board 첨부 다운로드 정책: board/views/attachments.py + services/attachments.py
- 인라인 업데이트 공용: board/services/inline_update.py

### (2) 운영 UI 중심 설계
- 게시판/서식/인라인 업데이트는 운영 흐름에 최적화
- Admin도 운영 UX의 일부로 간주

### (3) 점진적 확장 구조
- accounts는 기준점(인증/검색/권한)
- manual/board는 운영 앱 확장의 대표 사례
- partner/dash/commission 등도 동일 패턴으로 확장
