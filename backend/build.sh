#!/usr/bin/env bash
# Render build script
# Runs during each deploy to install deps, collect static, migrate, and seed.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_db
