# django_ma/docs/03_auth_and_permission.md

# 인증 및 권한 정책 (Auth & Permission)

본 문서는 django_ma 프로젝트 전반의  
**인증(Authentication)과 권한(Authorization) 정책의 기준 문서**이다.

accounts 앱의 구현을 SSOT로 하며,  
모든 앱은 본 문서의 원칙을 전제로 설계·구현된다.

---

## 1. 인증(Authentication)

- Django 기본 인증 시스템 사용
- CustomUser 모델 기반 인증
- `USERNAME_FIELD = "id"` (사번 기반 로그인)

### 인증 흐름 요약

Login Request
 → Django Auth
 → CustomUser 조회
 → is_active 확인
 → 인증 성공 / 실패

- 인증 단계에서 is_active=False인 경우 즉시 차단
- 프론트(UI) 노출 여부와 무관하게 서버에서 최종 판단

---

## 2. 사용자 상태(Status)
| status | 의미 |
|-----|-----|
| 재직 | 정상 활동 가능 |
| 퇴사 | 접근 제한 |

> 실제 로그인 가능 여부는 status가 아닌 `is_active`로 판단한다.  
> `inactive` 등급은 `is_active=False`로 로그인 차단한다.

### inactive 정책

- `grade == inactive`
  - `is_active = False`로 강제 설정
  - 로그인 및 모든 접근 불가
- 인증 폼(ActiveOnlyAuthenticationForm)과 서버 로직에서 이중 차단

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

## 4. 핵심 권한 규칙

- `grade == inactive` → `is_active = False`
- **모든 권한 판단은 grade 기준**
- 템플릿(UI)은 참고용일 뿐이며, **최종 차단은 서버(View/Decorator/Policy)에서 수행**

### 서버 접근 제어 기준

- `grade_required` 데코레이터 사용
- alias_map 지원
  - 예: `head`, `leader` → 역할 기반 권한 묶음
- inactive 계정은 데코레이터 단계에서 즉시 차단

---

## 5. 사용자 검색 권한 정책 (중요)

- 사용자 검색은 accounts/search_api.py를 SSOT로 사용
- 검색 결과는 항상 요청자의 권한 범위 내에서만 반환
- 프론트엔드에서는:
  - grade / branch / scope 판단을 하지 않는다
  - 결과를 그대로 표시만 한다

⚠️ 사용자 검색을 프론트에서 필터링하거나 자체 구현하는 것은 절대 금지

---

## 6. 앱별 접근 정책 예시

### 6-1. manual 앱

- 목록 노출과 상세 접근 권한은 다를 수 있음
- 템플릿(UI)은 참고용이며, **서버(View/Policy)에서 최종 판단**
- 상세 접근 차단은 `manual/utils/permissions.py`의 `manual_accessible_or_denied()`가 담당(SSOT)

| 조건 | 접근 가능 |
|----|----|
| admin_only=True | superuser, head |
| is_published=False | superuser |

> 참고:
> - 목록 노출은 `manual/views/pages.py::manual_list`의 필터링 규칙을 따른다.
> - 상세 접근은 `manual_accessible_or_denied()`에서 최종 차단(팝업 템플릿 렌더)한다.
> - 편집(AJAX) 권한은 `ensure_superuser_or_403()`로 일괄 차단한다.

### 6-2. board 앱 (리팩토링 완료 기준)

board 앱은 **업무요청·직원업무 처리 흐름을 담당하는 운영 중심 앱**이며,  
권한 정책은 UI 노출 여부와 무관하게 **서버에서 최종 판단**한다.

#### (1) Post (업무요청)

- **UI 정책(템플릿 기준)**  
  - superuser / head / leader에게 주요 기능 노출
  - 일반 사용자는 조회 및 제한된 기능만 제공

- **서버 정책(View 기준)**  
  - `grade_required` 데코레이터로 접근 제어
  - 작성자/담당자/상태 변경은 서버에서 권한 검증 후 처리

- **공통 원칙**  
  - 로그인 사용자만 접근 가능
  - 템플릿 노출 여부는 참고용이며,  
    **실제 권한은 서버에서 강제**

#### (2) Task (직원업무)

- **접근 정책**
  - superuser 전용 기능
  - 목록 / 상세 / 생성 / 수정 / 인라인 업데이트 모두 동일 정책

- **보안 원칙**
  - URL 직접 접근 시에도 superuser가 아니면 차단
  - 프론트 JS는 권한이 없으면 자동 종료하도록 설계

#### (3) 서식 (PDF 출력)

- **support_form (업무요청서)**
  - superuser / head / leader 중심 사용
  - 서버에서 접근 권한 최종 판단

- **states_form (FA 소명서)**
  - inactive 계정 접근 불가
  - 인증/권한 검증 후 PDF 생성

> 📌 PDF는 단순 출력물이 아니라  
> **개인정보·민감정보를 포함할 수 있으므로 서버 차단이 필수**

#### (4) 첨부 다운로드 보안 정책 (중요)

- ❌ `att.file.url` 직접 노출 **절대 금지**
- ✅ 반드시 **다운로드 뷰 + 권한 검증** 경유

| 구분 | 다운로드 URL name |
|------|------------------|
| Post 첨부 | `board:post_attachment_download` |
| Task 첨부 | `board:task_attachment_download` |

- 다운로드 뷰에서:
  - 로그인 여부 확인
  - 대상 객체 접근 권한 검증
  - FileResponse로 안전하게 제공

---

## 7. 설계 원칙 (Auth & Permission)

- 권한 분기 로직을 템플릿(UI)에만 의존하지 않는다
- **모든 접근 판단은 서버(View / Decorator / Policy)에서 최종 수행**
- 프론트엔드는:
  - 권한 판단을 하지 않는다
  - 서버 판단 결과를 그대로 반영한다
- 파일/개인정보는:
  - URL 직접 노출 금지
  - 다운로드 뷰 + 권한 검증 필수

➡️ **권한 정책을 우회하는 구현은 허용되지 않는다.**
