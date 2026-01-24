# 인증 및 권한 정책 (Auth & Permission)

## 1. 인증(Authentication)

- Django 기본 인증 시스템 사용
- USERNAME_FIELD = id (사원번호)
- CustomUser 기반

---

## 2. 사용자 상태(Status)

| status | 의미 |
|-----|-----|
| 재직 | 정상 활동 가능 |
| 퇴사 | 접근 제한 |

> status는 업무적 상태 표현이며  
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
- resign은 로그인 가능 여부 정책적으로 제한 가능
- 권한 판단은 grade 기준

---

## 5. 설계 원칙

- 권한 분기 로직은 View에 직접 작성하지 않는다
- 검색/접근 정책은 반드시 중앙화
