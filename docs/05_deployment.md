# django_ma/docs/05_deployment.md

# 배포 및 운영 (Deployment)

## 1. 환경 분리
- APP_ENV=dev / prod
- .env.dev / .env.prod 자동 로딩

---

## 2. 필수 서비스
- PostgreSQL
- Redis
- Celery Worker (사용하는 경우)

---

## 3. 운영 설정 특징
- DEBUG=False 시 보안 옵션 활성화
- Whitenoise Manifest 사용(정적 파일)
- 운영 DB 보호 로직 내장(있다면 활성 조건 문서화)

---

## 4. 정적 파일(CSS/JS) 운영 원칙
### 4-1) CSS 모듈화(최종 기준)
- `static/css/base.css` : 전역 토대/토큰/공통 컴포넌트
- `static/css/fixes.css` : 전역 충돌 방어(최소)
- `static/css/plugins/datatables.css` : DataTables 버튼/스킨 전용
- `static/css/apps/*.css` : 앱 단위 스코프 스타일

### 4-2) board 앱 적용 방식
- `base.html`은 core CSS만 전역 로드
- `board/base_board.html`에서만 `apps/board.css`를 로드
- content를 `<div class="board-scope">...</div>`로 감싸 스코프 누수 방지

---

## 5. 로그
- access.log 파일 기반(환경별 상이)
- django.security 별도 로거(권장)
- Celery 로그는 worker 기준
