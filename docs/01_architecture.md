# 프로젝트 아키텍처 (Architecture)

## 1. 전체 구조 개요

django_ma는 전통적인 Django MVT 구조를 기반으로 하되,
운영 편의성과 유지보수를 위해 다음과 같은 계층 분리를 따른다.

[ Browser ]
↓
[ Django Template ]
↓
[ View / API Wrapper ]
↓
[ Service / Policy Layer ]
↓
[ Model ]
↓
[ PostgreSQL / Redis ]


---

## 2. accounts 앱 기준 아키텍처



accounts/
├── models.py # CustomUser, 핵심 도메인 규칙
├── search_api.py # 사용자 검색 정책 (SSOT)
├── views.py # HTTP endpoint / wrapper
├── tasks.py # Celery 비동기 처리
├── admin.py # 관리자 UI + 업로드
├── constants.py # 캐시 키 / 공통 상수
├── urls.py # accounts 전용 URL
└── static/js/ # admin 업로드 JS


---

## 3. 핵심 설계 포인트

### (1) 검색 로직 단일화
- 모든 사용자 검색은 `search_api.py`에서만 구현
- views/api_views는 래퍼 역할만 수행
- 정책 변경 시 **한 파일만 수정**

### (2) 비동기 작업 분리
- 엑셀 업로드는 Celery task에서 처리
- View는 task 실행 + 진행률 조회만 담당

### (3) Cache 기반 상태 공유
- Redis cache로 진행률/상태 공유
- Admin UI는 polling 방식으로 상태 조회

---

## 4. 확장성 고려
- accounts 앱은 향후 모든 앱의 **권한/검색/사용자 기준점** 역할
- 다른 앱은 accounts 정책을 참조하는 구조로 확장 예정