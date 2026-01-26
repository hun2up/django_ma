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
- 블록 단위 콘텐츠 관리 (텍스트 / 이미지 / 첨부)
- 드래그 기반 정렬 및 섹션 간 이동
- grade 기반 접근 제어 (accounts 정책 연동)

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
| admin_only = True | superuser, head |
| is_published = False (직원전용) | superuser |
| 일반 매뉴얼 | superuser, head, leader, basic |

> 최종 접근 판단은 **서버(View)** 에서 수행한다.

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
│ ├── init.py
│ ├── pages.py # HTML Page View
│ ├── manual.py # Manual AJAX
│ ├── section.py # Section AJAX
│ ├── block.py # Block AJAX
│ └── attachment.py # Attachment AJAX
├── utils/
│ ├── init.py
│ ├── http.py # JSON 파싱 / 응답 통일
│ ├── permissions.py # 접근/권한 정책
│ ├── rules.py # 비즈니스 규칙
│ ├── parsing.py # 입력 파싱
│ └── serializers.py # 프런트 렌더용 dict 변환
└── templates/manual/

---

### (2) View 분리 원칙

- **pages.py**
  - HTML 렌더링 전용
  - 접근 권한 최종 판정 포함

- **manual / section / block / attachment**
  - 순수 AJAX 엔드포인트
  - JSON 응답만 반환
  - 권한 체크는 공통 유틸 사용

> View 파일은 **기능 단위로 분리**하며  
> urls.py / 기존 import 경로는 `views/__init__.py`에서 유지한다.

---

## 5. utils 패키지 설계

manual 앱의 핵심 설계 포인트 중 하나는
**비즈니스 규칙과 View 로직의 분리**이다.

### (1) utils/http.py
- json_body
- ok / fail
- 응답 포맷 통일

### (2) utils/permissions.py
- grade 판별
- superuser / head 여부
- 매뉴얼 접근 가능 여부 판단
- View에서 직접 grade 비교 금지

### (3) utils/rules.py
- 기본 섹션 자동 생성
- 공개 범위(access) → DB 플래그 변환

### (4) utils/serializers.py
- Block / Attachment를
  프런트가 즉시 DOM 업데이트 가능한 dict로 변환

> utils는 **SSOT(Single Source of Truth)** 역할을 한다.

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

## 7. 설계 원칙 요약

- **권한 판단은 View에서 직접 하지 않는다**
- **정책은 utils에 집중**
- **프런트는 서버 판단을 신뢰**
- **0개 상태를 허용하지 않는다**
- **정렬/이동은 항상 서버 기준으로 확정**

manual 앱은
> “운영자가 직접 쓰는 내부 시스템”  
을 기준으로 설계되었으며,

단기 기능 추가보다  
**장기 운영 / 유지보수 / 인수인계**를 우선한다.
