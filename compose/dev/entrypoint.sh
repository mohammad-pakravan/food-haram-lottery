#!/bin/bash

set -e

echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "Database is ready!"

echo "Creating migrations (if needed)..."
python manage.py makemigrations accounts --noinput || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting development server..."
exec python manage.py runserver 0.0.0.0:8000

