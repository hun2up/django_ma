# django_ma/docs/99_troubleshooting.md

# 트러블슈팅 가이드

## 1. 엑셀 업로드가 0%에서 멈춤
- Redis 연결 확인
- Celery worker 실행 여부 확인

---

## 2. 검색 결과가 안 나오는 경우
- search_api.py 정책 확인
- grade / scope / branch 점검

---

## 3. 로그인 안 되는 사용자
- grade == inactive 여부 확인
- is_active 값 확인

---

## 4. 매뉴얼은 보이는데 들어가면 권한 오류
- 목록 노출과 상세 접근 권한은 다를 수 있음
- manual_accessible_or_denied 로직 확인
- admin_only / is_published / grade 점검

---

## 5. 운영 DB 연결 차단 오류
- DEBUG=True 상태에서 운영 DB 연결 시도 여부 확인
