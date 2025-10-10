#!/usr/bin/env bash
# build.sh

# Install dependencies
pip install -r requirements.txt

# Collect static files (optional)
python manage.py collectstatic --noinput

# Run migrations
python manage.py makemigrations --noinput
python manage.py migrate --noinput