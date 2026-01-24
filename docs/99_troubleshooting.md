# 트러블슈팅 가이드

## 1. 엑셀 업로드가 0%에서 멈춤
- Redis 연결 확인
- Celery worker 실행 여부 확인
- upload_status cache 값 확인

---

## 2. 검색 결과가 안 나오는 경우
- search_api.py 정책 확인
- grade / scope / branch 파라미터 점검

---

## 3. 로그인 안 되는 사용자
- grade == inactive 여부 확인
- is_active 값 확인

---

## 4. 결과 엑셀 다운로드 안 됨
- upload_result_path cache 확인
- MEDIA_ROOT/upload_results 존재 여부 확인

---

## 5. 운영 DB 연결 차단 오류
- DEBUG=True 상태에서 운영 DB 연결 시도
- 의도된 안전 장치
