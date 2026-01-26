# django_ma/docs/04_background_tasks.md

# 배포 및 운영 (Deployment)

## 1. 환경 분리
- APP_ENV=dev / prod
- .env.dev / .env.prod 자동 로딩

---

## 2. 필수 서비스
- PostgreSQL
- Redis
- Celery Worker

---

## 3. 운영 설정 특징
- DEBUG=False 시 보안 옵션 활성화
- Whitenoise Manifest 사용# 배포 및 운영 (Deployment)

## 1. 환경 분리
- APP_ENV=dev / prod
- .env.dev / .env.prod 자동 로딩

---

## 2. 필수 서비스
- PostgreSQL
- Redis
- Celery Worker

---

## 3. 운영 설정 특징
- DEBUG=False 시 보안 옵션 활성화
- Whitenoise Manifest 사용
- 운영 DB 보호 로직 내장

---

## 4. 로그
- access.log 파일 기반
- django.security 별도 로거
- Celery 로그는 worker 기준

- 운영 DB 보호 로직 내장

---

## 4. 로그
- access.log 파일 기반
- django.security 별도 로거
- Celery 로그는 worker 기준
