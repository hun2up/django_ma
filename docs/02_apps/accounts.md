# accounts 앱 상세 문서

## 1. 앱의 책임 (Responsibility)

accounts 앱은 시스템 전반의 **사용자 식별과 권한의 기준점**이다.

- CustomUser 모델 정의
- 사용자 등급(grade) / 상태(status) 규칙 관리
- 로그인/접근 제어
- 사용자 검색 API 제공
- 관리자용 엑셀 업로드/다운로드

---

## 2. 주요 파일 설명

### models.py
- CustomUser 정의
- grade / status 규칙 내장
- inactive → is_active=False 강제

### search_api.py
- 사용자 검색 SSOT
- 권한/지점/팀 제한 정책 구현
- 모든 검색 API의 기준

### views.py
- upload_progress_view
- search API wrapper
- 로그인 관련 뷰

### tasks.py
- 엑셀 업로드 Celery task
- 대용량 사용자 업서트
- 결과 리포트 생성

### admin.py
- Django admin 확장
- 엑셀 업로드/다운로드 UI
- 커스텀 AdminSite 연동

---

## 3. 중요한 비즈니스 규칙

- inactive 계정은 무조건 로그인 불가
- 관리자 계정(superuser/admin/head 등)은
  엑셀 업로드로 등급 강등되지 않도록 보호
- 사용자 검색 결과는 **권한 범위 내에서만 반환**

