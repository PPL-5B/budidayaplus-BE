#!/bin/bash
set -e
set -x  # tampilkan semua perintah saat dieksekusi

# Flush database (hapus semua data)
docker-compose exec -T web python manage.py flush --noinput

# Load fixtures satu per satu
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/01_user.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/03_pond.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/04_cycle.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/05_pondfishamount.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/06_pondquality.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/07_fishdeath.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/08_fishsampling.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/09_foodsampling.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/seeding/fixtures/10_forum.json --verbosity 2
docker-compose exec -T web python manage.py loaddata /app/tasks/fixtures/data.json --verbosity 2
