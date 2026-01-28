# django_ma/docs/04_background_tasks.md

# 백그라운드 작업 (Background Tasks)

## 1. 개요
django_ma는 운영 편의성을 위해 일부 작업을 백그라운드로 처리한다.

- 대량 엑셀 업로드/정합성 처리
- 향후 예정: 대시보드 집계/캐시 워밍, 자동 알림, 리포트 생성 등

---

## 2. 구성 요소
- Broker/Cache: Redis
- Worker: Celery

---

## 3. 현재 사용 범위
### (1) accounts 앱
- 관리자 엑셀 업로드를 비동기로 처리(대량 처리/시간 소요 대응)
- 진행률/상태 업데이트(운영 UI/로그 기반)

### (2) board 앱
- 현재 board는 실시간 처리 중심
- PDF 생성은 요청 시 즉시 생성(ReportLab) 형태
- 향후 대량 PDF 생성/메일링 등이 필요하면 Celery로 이전 가능

---

## 4. 운영 체크리스트
- Redis 연결 확인
- Celery worker 실행 확인
- 배포 환경에서 .env(prod) 로딩 확인
- 대량 처리 시 worker concurrency 설정 점검

---

## 5. 로깅
- Celery 로그는 worker 기준으로 관리
- 장애 시 Redis 연결/Queue 적체 여부 확인
