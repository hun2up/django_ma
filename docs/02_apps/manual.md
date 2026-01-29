# django_ma/docs/02_apps/manual.md

# manual 앱 상세 문서

## 1. 앱의 책임 (Responsibility)

manual 앱은 조직 내부에서 사용하는 **업무 매뉴얼 관리 시스템**이다.

단순한 게시판이 아니라,
- 관리자에 의해 구조화된 문서
- 섹션/블록 단위 편집
- 권한(공개 범위)에 따른 접근 제어
를 전제로 설계되었다.

manual 앱의 핵심 책임은 다음과 같다.

- 업무 매뉴얼 생성 / 수정 / 삭제
- 매뉴얼 공개 범위(일반 / 관리자전용 / 직원전용) 관리
- 섹션(카드) 단위 구조화
- 블록 단위 콘텐츠 관리 (텍스트(HTML) / 이미지 / 첨부파일)
- 드래그 기반 정렬 및 섹션 간 이동
- grade 기반 접근 제어 (accounts 정책 연동)
- 템플릿/JS/CSS 모듈화(앱 CSS는 app_css 블록에서만 로드)

---

## 2. 핵심 개념 정리

### (1) Manual (매뉴얼)
- 하나의 업무 문서 단위
- 제목(title), 정렬순서(sort_order), 공개 범위 보유

### (2) Section (섹션 / 카드)
- 매뉴얼 내부의 논리적 구획
- 드래그로 순서 변경 가능
- 섹션이 0개가 되지 않도록 **기본 섹션 자동 보장**

### (3) Block (블록)
- 실제 콘텐츠 단위
- 섹션 내부에 포함
- 텍스트, 이미지, 첨부파일을 가질 수 있음
- 섹션 간 이동 가능

---

## 3. 접근 권한 정책 (Access Policy)

manual 앱의 접근 정책은 **accounts.grade**를 기준으로 한다.

### (1) 매뉴얼 접근 규칙

| 조건 | 접근 가능 |
|----|----|
| admin_only = True (관리자 전용) | 운영 정책에 따른 관리자 범위(예: superuser / head / leader) |
| is_published = False (직원 전용) | 운영 정책에 따른 내부 사용자 범위(예: superuser) |
| 일반 매뉴얼 | 로그인 사용자(권한 정책에 따라 필터링) |

> ✅ 최종 접근 판단은 **서버(View)** 에서 수행한다.  
> 문서의 “접근 가능 등급”은 운영 정책에 따라 조정될 수 있으므로, **View 로직(필터/권한체크)을 SSOT로 본다.**
 

---

### (2) 편집 권한 규칙

| 기능 | 허용 등급 |
|----|----|
| 매뉴얼 생성/삭제 | superuser |
| 섹션 추가/삭제/정렬 | superuser |
| 블록 추가/수정/삭제 | superuser |
| 첨부파일 업로드 | superuser |

> head / leader는 **열람만 가능**  
> 편집 권한은 명확히 superuser로 제한한다.

---

## 4. 아키텍처 구조

### (1) 전체 구조

manual/
├── models.py
├── constants.py
├── forms.py
├── urls.py
├── views/
│ ├── __init__.py
│ │   └── 모든 view callable re-export (__all__ 포함, SSOT)
│ ├── pages.py        # HTML Page View (목록/상세/폼)
│ ├── manual.py       # Manual AJAX (생성/수정/삭제/정렬)
│ ├── section.py      # Section AJAX (카드 CRUD/정렬)
│ ├── block.py        # Block AJAX (블록 CRUD/이동/정렬)
│ └── attachment.py   # Attachment AJAX (첨부 업로드/삭제)
├── utils/
│ ├── __init__.py
│ │   └── utils 공식 export (SSOT)
│ ├── http.py         # JSON 파싱 / ok·fail 응답 통일
│ ├── permissions.py # 접근/노출/편집 권한 정책 (SSOT)
│ ├── rules.py        # 비즈니스 규칙 (기본 섹션 보장 등)
│ ├── parsing.py      # 입력 파싱 유틸
│ └── serializers.py  # 프런트 즉시 렌더용 dict 변환
└── templates/manual/

---

### (2) View 분리 원칙

- **pages.py**
  - HTML 렌더링 전용
  - 접근 권한 최종 판정 포함
  - 목록 노출 정책은 utils.permissions의 SSOT 함수를 사용

- **manual / section / block / attachment (AJAX 전용)**
  - 순수 AJAX 엔드포인트
  - JSON 응답만 반환
  - 권한 체크는 utils.permissions.ensure_superuser_or_403 사용
  - 파싱/검증/직렬화는 utils에 위임
  - 트랜잭션 단위로 데이터 정합성 보장

> ❗️manual/views.py(모놀리식)는 제거되었으며  
> **모든 외부 접근은 `views/__init__.py` re-export + `__all__`을 통해서만 허용**한다.

---

## 5. 프런트엔드(템플릿/JS/CSS) 구조

manual 앱은 “운영자가 직접 쓰는 내부 시스템” 성격상, UI/편집 흐름이 중요하다.

### (1) CSS 모듈화 (apps/manual.css)
- `base.html`은 코어 CSS만 로드하고, 앱별 CSS는 `{% block app_css %}`에서만 로드한다.
- `manual_list.html`, `manual_detail.html`에서 아래처럼 manual.css를 명시적으로 로드해야 한다.
  - 예: `{% block app_css %}<link rel="stylesheet" href="{% static 'css/apps/manual.css' %}">{% endblock %}`

### (2) 공통 검색 모달 호환 (base.css)
- `base.css`에는 검색 결과 hover UX 규칙이 있으며,
  `components/search_user_modal.html`의 결과 컨테이너 id가 `searchResults`로 유지되어야 한다.
- 현재 템플릿은 `<div id="searchResults" class="mt-3"></div>`로 유지 중이며 호환된다.

### (3) wide layout 정책 (manual.css)
- `#manual-detail`은 viewport 기반 폭(`72vw`) + max-width 토큰을 사용한다.
- manual 페이지가 기본 container wrapper를 사용하지 않을 수 있으므로,
  wide layout은 **wrapper 구조가 변해도 가운데 정렬이 유지되도록** `margin-left/right:auto` 기반으로 설계한다.

+### (4) JS 모듈 구조
+- 목록: `manual_list_boot.js` + `manual_list_edit.js` (superuser 편집모드/정렬/삭제/일괄수정)
+- 상세:
  - `manual_detail_subnav.js` (sticky subnav / active 처리)
  - `manual_detail_section_sort.js` (섹션 정렬)
  - `manual_detail_block/*` (Quill 편집/블록 CRUD/첨부 업로드/블록 정렬)

> 프런트는 서버 응답(JSON) 기반으로 DOM을 갱신하며, 페이지는 BFCache/중복 바인딩 가드를 포함한다.

---

## 6. 정렬 및 이동 정책

### (1) 매뉴얼 정렬
- manual.sort_order 기준
- drag & drop → reorder API

### (2) 섹션 정렬
- manual_id 기준으로만 정렬 허용
- 외부 섞임 방지 로직 포함

### (3) 블록 이동
- 같은 매뉴얼 내 섹션 간 이동만 허용
- 이동 시:
  - source 섹션 정렬
  - target 섹션 정렬
  - 트랜잭션으로 처리

---

## 6-1. 권한/노출 정책 SSOT 위치

- **목록 노출 정책**: `utils.permissions.filter_manuals_for_user`
- **상세 접근 판정**: `utils.permissions.manual_accessible_or_denied`
- **편집 권한 차단**: `utils.permissions.ensure_superuser_or_403`

→ View/템플릿/JS 어디에서도 grade를 직접 비교하지 않는다.

---

## 7. 설계 원칙 요약

- **접근/권한은 서버(View)에서 최종 판정**
- **프런트는 서버 판단을 신뢰**
- **섹션 0개 상태를 허용하지 않는다(기본 섹션 보장)**
- **정렬/이동은 항상 서버 기준으로 확정**
- **앱 CSS는 base.html이 아닌 app_css 블록에서만 로드(모듈화)**
- **View/권한/노출 정책은 utils를 SSOT로 유지**

manual 앱은
> “운영자가 직접 쓰는 내부 시스템”  
을 기준으로 설계되었으며,

단기 기능 추가보다  
**장기 운영 / 유지보수 / 인수인계**를 우선한다.
