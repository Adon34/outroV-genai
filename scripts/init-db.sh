#!/bin/bash
# scripts/init-db.sh

set -e

echo "Waiting for PostgreSQL to start..."
while ! nc -z postgres 5432; do
    sleep 1
done
echo "PostgreSQL started"

echo "Waiting for Redis to start..."
while ! nc -z redis 6379; do
    sleep 1
done
echo "Redis started"

echo "Waiting for ChromaDB to start..."
while ! nc -z chroma-db 8000; do
    sleep 1
done
echo "ChromaDB started"

echo "Initializing database..."
cd /app/backend
alembic upgrade head

echo "Loading initial data..."
python scripts/seed-data.js

echo "Database initialized successfully"