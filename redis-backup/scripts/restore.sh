#!/bin/bash
#
# Redis Restore Script
# 從備份還原 Redis 資料
#

set -e

# Configuration
BACKUP_API_URL="${BACKUP_API_URL:-http://localhost:8080}"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    curl -s "$BACKUP_API_URL/api/v1/backups" | python3 -m json.tool
    exit 1
fi

echo "=== Redis Restore ==="
echo "API URL: $BACKUP_API_URL"
echo "Backup File: $BACKUP_FILE"
echo ""

# Confirm
read -p "Are you sure you want to restore from $BACKUP_FILE? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled"
    exit 0
fi

# Trigger restore
echo "Starting restore..."
RESPONSE=$(curl -s -X POST "$BACKUP_API_URL/api/v1/restore" \
    -H "Content-Type: application/json" \
    -d "{\"backup_file\": \"$BACKUP_FILE\", \"create_snapshot\": true, \"validate_after\": true}")

echo "Response: $RESPONSE"

STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" = "STARTED" ]; then
    echo ""
    echo "=== Restore Started ==="
    echo "A pre-restore snapshot has been created."
    echo "Please check the logs for completion status."
else
    echo ""
    echo "=== Restore Failed to Start ==="
    echo "$RESPONSE"
    exit 1
fi
