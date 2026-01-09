#!/bin/sh
# ============================================
# MinIO 備份腳本
# ============================================

set -e

# 載入配置
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

# 預設值
MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_USE_SSL="${MINIO_USE_SSL:-false}"
BACKUP_BUCKET="${BACKUP_BUCKET:-data}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_COMPRESSION_ENABLED="${BACKUP_COMPRESSION_ENABLED:-true}"
BACKUP_ENCRYPTION_ENABLED="${BACKUP_ENCRYPTION_ENABLED:-false}"

LOG_DIR="$BACKUP_DIR/logs"
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/backup_${TIMESTAMP}.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 設定 mc alias
setup_mc() {
    local protocol="http"
    [ "$MINIO_USE_SSL" = "true" ] && protocol="https"
    
    mc alias set backup "${protocol}://${MINIO_ENDPOINT}" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api S3v4
}

# 執行備份
do_backup() {
    log "===== MinIO BACKUP START ====="
    log "  Endpoint: $MINIO_ENDPOINT"
    log "  Bucket: $BACKUP_BUCKET"
    
    setup_mc
    
    # 檢查 bucket 是否存在
    if ! mc ls "backup/${BACKUP_BUCKET}" >/dev/null 2>&1; then
        error_exit "Bucket not found: $BACKUP_BUCKET"
    fi
    
    # 決定檔案副檔名
    local ext=".tar"
    [ "$BACKUP_COMPRESSION_ENABLED" = "true" ] && ext=".tar.gz"
    [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ] && ext="${ext}.enc"
    
    local backup_file="${BACKUP_DIR}/minio_backup_${TIMESTAMP}${ext}"
    local temp_dir="${BACKUP_DIR}/temp_${TIMESTAMP}"
    
    mkdir -p "$temp_dir"
    
    # 下載資料
    log "Downloading from MinIO..."
    mc cp --recursive "backup/${BACKUP_BUCKET}/" "$temp_dir/"
    
    # 打包
    log "Creating archive..."
    if [ "$BACKUP_COMPRESSION_ENABLED" = "true" ] && [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
        tar -czf - -C "$temp_dir" . | \
            openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -out "$backup_file"
    elif [ "$BACKUP_COMPRESSION_ENABLED" = "true" ]; then
        tar -czf "$backup_file" -C "$temp_dir" .
    elif [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
        tar -cf - -C "$temp_dir" . | \
            openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -out "$backup_file"
    else
        tar -cf "$backup_file" -C "$temp_dir" .
    fi
    
    # 清理暫存
    rm -rf "$temp_dir"
    
    local file_size=$(du -h "$backup_file" | cut -f1)
    log "Backup completed: $backup_file ($file_size)"
    
    # 清理過期備份
    log "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "minio_backup_*" -type f -mtime +$BACKUP_RETENTION_DAYS -delete
    
    log "===== MinIO BACKUP COMPLETE ====="
}

do_backup
