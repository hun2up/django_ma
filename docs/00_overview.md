# django_ma 프로젝트 개요 (Overview)

## 1. 프로젝트 목적
django_ma는 보험 GA 조직의 내부 업무를 지원하기 위한 Django 기반 웹 플랫폼이다.

현재 1차 목표는 **사용자(설계사/관리자) 계정 관리의 표준화와 자동화**이며,
향후 조직관리, 요율변경, 수수료/채권, 매출 대시보드 등으로 확장된다.

본 문서는 프로젝트를 처음 접하는 개발자 또는
유지보수/인수인계 대상자를 위한 최상위 개요 문서이다.

---

## 2. 현재 범위 (Scope)
> 현재 단계에서는 `accounts` 앱만 존재한다고 가정한다.

- CustomUser 모델 기반 사용자 관리
- 사용자 권한(grade) 및 상태(status) 관리
- 관리자(Admin) 엑셀 업로드/다운로드
- 사용자 검색 API (공통 모달용)
- Celery + Redis 기반 비동기 업로드 처리

---

## 3. 핵심 사용자 등급 (Grade)

| grade | 설명 |
|-----|-----|
| superuser | 시스템 최고 관리자 (각 영업부문별 한개씩 관리예정) |
| admin | (추가 예정) 직원 관리자 |
| head | 각 파트너별 최상위 관리자 |
| leader | 각 파트너별 중간 관리자 |
| basic | 일반 사용자(설계사) |
| resign | 퇴사자 |
| inactive | 비활성/마스킹 계정 |

> `resign`, `inactive`는 **업무 접근 제한 대상**이며  
> `inactive`는 시스템 레벨에서 로그인 불가 처리된다.

---

## 4. 기술 스택 요약

- Backend: Django 5.2
- Auth: CustomUser + Django Auth
- DB: PostgreSQL
- Cache/Broker: Redis
- Background Task: Celery
- Frontend: Django Template + Vanilla JS
- Infra: Linux / Nginx / Render (또는 유사 환경)

---

## 5. 설계 원칙

- **SSOT (Single Source of Truth)**  
  → 검색 정책, 권한 정책은 단일 파일에서 관리
- **비즈니스 규칙은 코드보다 문서에 먼저 기록**
- **Admin 기능도 운영 UI로 간주**
- **장기 운영 + 인수인계 가능성 전제**

