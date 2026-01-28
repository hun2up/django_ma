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
> `inactive` 등급은 `is_active=False`로 로그인 차단한다.

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
- 프론트(UI) 노출과 무관하게 서버에서 최종 차단

---

## 5. 앱별 접근 정책 예시

### (1) manual 앱
- 목록 노출과 상세 접근 권한은 다를 수 있음
- 조건에 따라 서버에서 최종 판단

| 조건 | 접근 가능 |
|----|----|
| admin_only=True | superuser, head |
| is_published=False | superuser |

### (2) board 앱(리팩토링 완료 기준)

#### 2-1) Post(업무요청) 접근
- 화면 정책(템플릿): superuser/head/leader에게 주요 기능 노출
- 서버 정책(뷰): grade_required 등으로 최종 판단(권장)
- 공통: 로그인 사용자 대상

#### 2-2) Task(직원업무) 접근
- superuser 전용
- task_list/task_detail 및 인라인 업데이트 모두 superuser만 사용

#### 2-3) 서식(PDF) 접근
- support_form(업무요청서): superuser/head/leader 중심
- states_form(FA 소명서): inactive 계정 접근 제한(서버에서 최종 차단 권장)

#### 2-4) 첨부 다운로드 보안 정책(중요)
- `att.file.url` 직접 노출 금지
- 반드시 다운로드 뷰(권한검증 포함) 경유
  - Post: `board:post_attachment_download`
  - Task: `board:task_attachment_download`

---

## 6. 설계 원칙
- 권한 분기 로직을 템플릿에만 의존하지 않는다(안내용 UI는 가능)
- 권한 판단은 서버(View/Decorator/Policy)에서 최종 수행
- 파일/개인정보는 URL 직접 노출 금지(다운로드 뷰 + 권한검증)
