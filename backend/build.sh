#!/usr/bin/env bash
# Render build: install, collect static, migrate (creates the DB_SCHEMA schema), seed demo data.
set -o errexit -o nounset -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_db
