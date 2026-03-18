#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="diet_chatbot"
DB_USER="postgres"

echo "Starting backup at $(date)"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker exec diet_postgres pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/postgres_$DATE.sql

# Backup Redis
echo "Backing up Redis..."
docker exec diet_redis redis-cli SAVE
docker cp diet_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup ChromaDB
echo "Backing up ChromaDB..."
tar -czf $BACKUP_DIR/chromadb_$DATE.tar.gz -C /var/lib/docker/volumes/diet-chatbot_chroma_data/_data .

# Compress PostgreSQL backup
gzip $BACKUP_DIR/postgres_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed at $(date)"