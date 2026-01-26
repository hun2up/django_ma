# django_ma/docs/03_auth_and_permission.md

# 인증 및 권한 정책 (Auth & Permission)

## 1. 인증(Authentication)

- Django 기본 인증 시스템 사용
- CustomUser 기반
- USERNAME_FIELD = id (사원번호)

---

## 2. 사용자 상태(Status)

| status | 의미 |
|-----|-----|
| 재직 | 정상 활동 가능 |
| 퇴사 | 접근 제한 |

> 실제 로그인 가능 여부는 `is_active`로 판단한다.

---

## 3. 사용자 등급(Grade) 정책

| grade | 로그인 | 권한 |
|-----|-----|-----|
| superuser | 가능 | 전체 |
| admin | 가능 | 운영 |
| head | 가능 | 조직 |
| leader | 가능 | 팀 |
| basic | 가능 | 본인 |
| resign | 가능 | 제한 |
| inactive | 불가 | 없음 |

---

## 4. 핵심 규칙

- grade == inactive → is_active = False
- 권한 판단은 **grade 기준**
- View는 직접 판단하지 않는다

---

## 5. 앱별 접근 정책 예시 (manual 앱)

- 매뉴얼 접근은 서버(View)에서 최종 판단
- 프런트 노출 여부와 무관하게 권한 차단

| 조건 | 접근 가능 |
|----|----|
| admin_only=True | superuser, head |
| is_published=False | superuser |

---

## 6. 설계 원칙

- 권한 분기 로직은 View에 직접 작성하지 않는다
- 접근 정책은 utils/permissions 레이어에서 중앙 관리
