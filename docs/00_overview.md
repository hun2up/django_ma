# django_ma/docs/00_overview.md

# django_ma 프로젝트 개요 (Overview)

## 1. 프로젝트 목적
django_ma는 보험 GA 조직의 내부 업무를 지원하기 위한 Django 기반 웹 플랫폼이다.

초기 목표는 **사용자(설계사/관리자) 계정 관리의 표준화와 자동화**이며,
이를 기반으로 다음과 같은 내부 운영 시스템으로 확장된다.

- 업무 매뉴얼 기반 지식 관리
- 조직/권한 관리
- 업무요청/직원업무 처리 흐름(게시판)
- 요율변경 및 수수료/채권 관리
- 매출 현황 및 예측 대시보드

본 문서는 프로젝트를 처음 접하는 개발자 또는
유지보수/인수인계 대상자를 위한 **최상위 개요 문서**이다.

---

## 2. 현재 범위 (Scope)

현재 django_ma는 아래 앱들로 구성되며, 운영 시스템으로 점진 확장 중이다.

### (1) accounts 앱
- CustomUser 모델 기반 사용자 관리
- 사용자 권한(grade) 및 상태(status) 관리
- 관리자(Admin) 엑셀 업로드/다운로드
- 사용자 검색 API (SSOT, 권한 범위 서버 강제)
- affiliation_display 기반 공통 검색 응답
- Celery + Redis 기반 비동기 엑셀 업로드
  - 진행률 polling
  - 결과 리포트 다운로드

### (2) manual 앱
- 내부 업무 매뉴얼(지식) 관리
- 섹션/블록 기반 콘텐츠 구조
- grade 기반 접근 제어(서버에서 최종 판정)
- 운영자(superuser) 중심의 관리 UI(목록/상세 편집 플로우)
- AJAX 기반 편집/정렬/이동(섹션/블록/첨부)
- View는 views 패키지로 기능 분리(pages/manual/section/block/attachment)
- utils 패키지로 파싱/응답/권한/규칙/직렬화 중앙화(SSOT)
- CSS 모듈화: manual 페이지는 app_css 블록에서만 apps/manual.css 로드

### (3) board 앱 (리팩토링 완료)
- **업무요청 게시판(Post)**: 요청 등록/조회/수정/삭제 + 댓글 + 첨부
- **직원업무 게시판(Task)**: superuser 전용 내부 업무 처리
- **인라인 상태/담당자 업데이트**: 목록/상세에서 AJAX로 즉시 반영
- **서식 출력(PDF)**: 업무요청서(support_form), FA 소명서(states_form)
- **보안 첨부 다운로드**: `att.file.url` 직접 노출 금지, 다운로드 뷰로만 제공
- **프론트 구조**: Bootstrap + Vanilla JS + 공용 includes(partials)
- **CSS 모듈화**: `static/css/apps/board.css`를 board 스코프에서만 로드
  - base.css: 전역 토대/토큰/공통 UI
  - apps/*.css: 앱 단위 스코프 스타일
  - board는 `board/base_board.html`에서만 `apps/board.css`를 로드
  - manual은 `manual_list.html`, `manual_detail.html`에서 `apps/manual.css`를 app_css 블록으로 로드

---

## 3. 핵심 사용자 등급 (Grade)

| grade | 설명 |
|-----|-----|
| superuser | 시스템 최고 관리자 |
| admin | (추가 예정) 직원 관리자 |
| head | 각 파트너별 최상위 관리자 |
| leader | 각 파트너별 중간 관리자 |
| basic | 일반 사용자(설계사) |
| resign | 퇴사자(접근 제한) |
| inactive | 비활성/마스킹 계정(로그인 불가) |

> `resign`, `inactive`는 **업무 접근 제한 대상**이며  
> `inactive`는 시스템 레벨에서 로그인 불가 처리된다.

---

## 4. 기술 스택 요약
- Backend: Django 5.2
- Auth: CustomUser + Django Auth
- DB: PostgreSQL
- Cache/Broker: Redis
- Background Task: Celery (주로 accounts 엑셀 업로드 등)
- Frontend: Django Template + Vanilla JS + Bootstrap 5
- PDF: ReportLab (board 서식 출력)
- Infra: Linux / Nginx / Render (또는 유사 환경)

---

## 5. 설계 원칙
- **SSOT (Single Source of Truth)**  
  → 검색 정책, 권한 정책, 다운로드 정책은 단일 위치에서 관리
- **비즈니스 규칙은 코드보다 문서에 먼저 기록**
- **운영 UI 중심 설계** (Admin도 운영 UX)
- **장기 운영 + 인수인계 가능성 전제**
- **CSS 모듈화/스코프 원칙 준수**
  - base.css: 전역 토대/토큰/공통 UI
  - apps/*.css: 앱 단위 스코프 스타일
  - board는 `board/base_board.html`에서만 `apps/board.css`를 로드
