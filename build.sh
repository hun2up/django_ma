#!/usr/bin/env bash
# django_ma/build.sh

# 빌드 실패 방지를 위한 안전 설정
set -o errexit  # 에러 발생 시 즉시 종료

# Install dependencies
pip install -r requirements.txt

# Collect static files (optional)
python manage.py collectstatic --noinput

# Run migrations
python manage.py makemigrations --noinput
python manage.py migrate --noinput