#!/bin/sh
set -eu

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py load_demo_data

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
