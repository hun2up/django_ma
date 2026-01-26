# django_ma/docs/01_architecture.md

# 프로젝트 아키텍처 (Architecture)

## 1. 전체 구조 개요

django_ma는 Django MVT 구조를 기반으로 하되,
운영 편의성과 유지보수를 위해 다음과 같은 계층 분리를 따른다.

[ Browser ]
↓
[ Django Template ]
↓
[ View / API Wrapper ]
↓
[ Policy / Rule Layer ]
↓
[ Model ]
↓
[ PostgreSQL / Redis ]

---

## 2. accounts 앱 기준 아키텍처

accounts/
├── models.py        # CustomUser, 핵심 도메인 규칙
├── search_api.py    # 사용자 검색 정책 (SSOT)
├── views.py         # HTTP endpoint / wrapper
├── tasks.py         # Celery 비동기 처리
├── admin.py         # 관리자 UI + 업로드
├── constants.py     # 공통 상수
├── urls.py
└── static/js/

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
│   └── http.py             # JSON 응답
├── constants.py
└── urls.py

---

## 4. 핵심 설계 포인트

### (1) 정책/규칙 중앙화
- 접근 권한: utils/permissions.py
- 비즈니스 규칙: utils/rules.py
- View는 **판단이 아닌 호출자 역할**

### (2) 운영 UI 중심 설계
- manual 앱은 내부 운영자용 기준 앱
- Admin 기능도 하나의 사용자 경험으로 설계

### (3) 점진적 확장 구조
- accounts는 기준점
- manual은 운영 앱의 첫 사례
- 이후 partner / dash 앱도 동일 패턴으로 확장
