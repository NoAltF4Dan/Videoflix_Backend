#!/bin/sh
set -e

echo "Warte auf PostgreSQL auf $DB_HOST:$DB_PORT..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  echo "PostgreSQL ist nicht erreichbar – schlafe 1 Sekunde..."
  sleep 1
done

echo "PostgreSQL ist bereit."

echo "Starte RQ Worker..."
exec python manage.py rqworker default