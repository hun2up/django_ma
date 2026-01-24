# 백그라운드 작업 (Background Tasks)

## 1. 사용 목적

- 대용량 엑셀 업로드 처리
- 사용자 계정 일괄 생성/수정
- UI 블로킹 방지

---

## 2. 기술 구성

- Celery
- Redis (Broker + Cache)
- Django ORM

---

## 3. 주요 Task

### process_users_excel_task
- 파일 경로 기반 엑셀 로딩
- 사용자 업서트
- 진행률 계산
- 결과 엑셀 생성

---

## 4. 진행률 처리 방식

- Redis cache 사용
- task_id 기준 키 구성
  - upload_progress:{task_id}
  - upload_status:{task_id}
  - upload_result_path:{task_id}

---

## 5. 실패 처리

- 예외 발생 시 status=FAILURE
- error 메시지 cache 저장
- Admin UI에 즉시 노출
