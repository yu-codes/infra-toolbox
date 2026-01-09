#!/bin/sh
# ============================================
# MinIO 還原腳本
# ============================================

set -e

# 載入配置
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

# 還原配置
RESTORE_ENDPOINT="${RESTORE_MINIO_ENDPOINT:-$MINIO_ENDPOINT}"
RESTORE_ACCESS="${RESTORE_MINIO_ACCESS_KEY:-$MINIO_ACCESS_KEY}"
RESTORE_SECRET="${RESTORE_MINIO_SECRET_KEY:-$MINIO_SECRET_KEY}"
RESTORE_BUCKET_NAME="${RESTORE_BUCKET:-$BACKUP_BUCKET}"
MINIO_USE_SSL="${MINIO_USE_SSL:-false}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

LOG_DIR="$BACKUP_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/restore_${TIMESTAMP}.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

setup_mc() {
    local protocol="http"
    [ "$MINIO_USE_SSL" = "true" ] && protocol="https"
    
    mc alias set restore "${protocol}://${RESTORE_ENDPOINT}" "$RESTORE_ACCESS" "$RESTORE_SECRET" --api S3v4
}

detect_file_type() {
    local file="$1"
    local is_encrypted=false
    local is_compressed=false
    
    case "$file" in
        *.enc)
            is_encrypted=true
            case "$file" in
                *.gz.enc) is_compressed=true ;;
            esac
            ;;
        *.gz) is_compressed=true ;;
    esac
    
    echo "$is_encrypted:$is_compressed"
}

do_restore() {
    local backup_file="$1"
    
    [ ! -f "$backup_file" ] && error_exit "Backup file not found: $backup_file"
    
    log "===== MinIO RESTORE START ====="
    log "  Backup file: $backup_file"
    log "  Target: $RESTORE_ENDPOINT / $RESTORE_BUCKET_NAME"
    
    setup_mc
    
    # 檢測檔案類型
    local file_type=$(detect_file_type "$backup_file")
    local is_encrypted=$(echo "$file_type" | cut -d: -f1)
    local is_compressed=$(echo "$file_type" | cut -d: -f2)
    
    local temp_dir="${BACKUP_DIR}/restore_temp_${TIMESTAMP}"
    mkdir -p "$temp_dir"
    
    log "Extracting backup..."
    if [ "$is_encrypted" = "true" ] && [ "$is_compressed" = "true" ]; then
        openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$backup_file" | tar -xzf - -C "$temp_dir"
    elif [ "$is_encrypted" = "true" ]; then
        openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$backup_file" | tar -xf - -C "$temp_dir"
    elif [ "$is_compressed" = "true" ]; then
        tar -xzf "$backup_file" -C "$temp_dir"
    else
        tar -xf "$backup_file" -C "$temp_dir"
    fi
    
    # 建立 bucket (若不存在)
    mc mb "restore/${RESTORE_BUCKET_NAME}" 2>/dev/null || true
    
    # 上傳資料
    log "Uploading to MinIO..."
    mc cp --recursive "$temp_dir/" "restore/${RESTORE_BUCKET_NAME}/"
    
    # 清理暫存
    rm -rf "$temp_dir"
    
    log "===== MinIO RESTORE COMPLETE ====="
}

list_backups() {
    log "Available backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/minio_backup_* 2>/dev/null || echo "  (none)"
}

usage() {
    echo "Usage: $0 [restore <backup_file>|list]"
    echo ""
    echo "Commands:"
    echo "  restore <file> - Restore from backup file"
    echo "  list           - List available backups"
    exit 1
}

case "${1:-}" in
    restore)
        [ -z "$2" ] && error_exit "Backup file path is required"
        do_restore "$2"
        ;;
    list)
        list_backups
        ;;
    *)
        usage
        ;;
esac
