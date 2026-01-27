#!/bin/bash
#
# Redis Backup Script
# 手動備份 Redis 資料
#

set -e

# Configuration
BACKUP_API_URL="${BACKUP_API_URL:-http://localhost:8080}"
LABEL="${1:-manual}"

echo "=== Redis Backup ==="
echo "API URL: $BACKUP_API_URL"
echo "Label: $LABEL"
echo ""

# Trigger backup
echo "Triggering backup..."
RESPONSE=$(curl -s -X POST "$BACKUP_API_URL/api/v1/backup/trigger" \
    -H "Content-Type: application/json" \
    -d "{\"label\": \"$LABEL\"}")

echo "Response: $RESPONSE"

# Extract task ID
TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TASK_ID" ]; then
    echo "Error: Failed to get task ID"
    exit 1
fi

echo "Task ID: $TASK_ID"
echo ""

# Wait for completion
echo "Waiting for backup to complete..."
MAX_WAIT=300
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s "$BACKUP_API_URL/api/v1/backup/status/$TASK_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo "Status: $STATUS"
    
    if [ "$STATUS" = "COMPLETED" ]; then
        echo ""
        echo "=== Backup Completed Successfully ==="
        echo "$STATUS_RESPONSE"
        exit 0
    elif [ "$STATUS" = "FAILED" ]; then
        echo ""
        echo "=== Backup Failed ==="
        echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
done

echo "Error: Backup did not complete within $MAX_WAIT seconds"
exit 1
