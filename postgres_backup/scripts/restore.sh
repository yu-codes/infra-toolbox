#!/bin/sh
# ============================================
# PostgreSQL 還原腳本
# 支援: 解密 + 解壓縮 + 還原
# ============================================

set -e

# 載入配置
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

# 使用還原專用配置，若無則使用備份配置
RESTORE_HOST="${RESTORE_POSTGRES_HOST:-$POSTGRES_HOST}"
RESTORE_PORT="${RESTORE_POSTGRES_PORT:-$POSTGRES_PORT}"
RESTORE_USER="${RESTORE_POSTGRES_USERNAME:-$POSTGRES_USERNAME}"
RESTORE_PASS="${RESTORE_POSTGRES_PASSWORD:-$POSTGRES_PASSWORD}"
RESTORE_DB="${RESTORE_POSTGRES_DATABASE:-$POSTGRES_DATABASE}"
RESTORE_DROP="${RESTORE_DROP_DATABASE:-false}"
RESTORE_CREATE="${RESTORE_CREATE_DATABASE:-true}"

# 預設值
RESTORE_HOST="${RESTORE_HOST:-postgres}"
RESTORE_PORT="${RESTORE_PORT:-5432}"
RESTORE_USER="${RESTORE_USER:-postgres}"

BACKUP_DIR="${BACKUP_DIR:-/backups}"
LOG_DIR="$BACKUP_DIR/logs"

mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/restore_${TIMESTAMP}.log"

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 檢測備份檔案類型
detect_file_type() {
    local file="$1"
    local is_encrypted=false
    local is_compressed=false
    
    case "$file" in
        *.enc)
            is_encrypted=true
            case "$file" in
                *.gz.enc)
                    is_compressed=true
                    ;;
            esac
            ;;
        *.gz)
            is_compressed=true
            ;;
    esac
    
    echo "$is_encrypted:$is_compressed"
}

# 還原資料庫
do_restore() {
    local backup_file="$1"
    
    [ ! -f "$backup_file" ] && error_exit "Backup file not found: $backup_file"
    
    log "===== RESTORE START ====="
    log "  Backup file: $backup_file"
    log "  Target: $RESTORE_HOST:$RESTORE_PORT/$RESTORE_DB"
    log "  User: $RESTORE_USER"
    
    # 檢測檔案類型
    local file_type=$(detect_file_type "$backup_file")
    local is_encrypted=$(echo "$file_type" | cut -d: -f1)
    local is_compressed=$(echo "$file_type" | cut -d: -f2)
    
    log "  Encrypted: $is_encrypted"
    log "  Compressed: $is_compressed"
    
    # 驗證加密密碼
    if [ "$is_encrypted" = "true" ] && [ -z "$BACKUP_ENCRYPTION_PASSWORD" ]; then
        error_exit "BACKUP_ENCRYPTION_PASSWORD is required for encrypted backups"
    fi
    
    export PGPASSWORD="$RESTORE_PASS"
    
    # 刪除現有資料庫 (若啟用)
    if [ "$RESTORE_DROP" = "true" ]; then
        log "Dropping existing database: $RESTORE_DB"
        psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS \"$RESTORE_DB\";" 2>/dev/null || true
    fi
    
    # 建立資料庫 (若啟用)
    if [ "$RESTORE_CREATE" = "true" ]; then
        log "Creating database: $RESTORE_DB"
        psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d postgres \
            -c "CREATE DATABASE \"$RESTORE_DB\";" 2>/dev/null || log "Database already exists"
    fi
    
    # 還原資料
    log "Restoring data..."
    
    if [ "$is_encrypted" = "true" ] && [ "$is_compressed" = "true" ]; then
        # 解密 + 解壓縮
        openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$backup_file" | \
            gunzip | \
            psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d "$RESTORE_DB"
    elif [ "$is_encrypted" = "true" ]; then
        # 僅解密
        openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$backup_file" | \
            psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d "$RESTORE_DB"
    elif [ "$is_compressed" = "true" ]; then
        # 僅解壓縮
        gunzip -c "$backup_file" | \
            psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d "$RESTORE_DB"
    else
        # 純文字
        psql -h "$RESTORE_HOST" -p "$RESTORE_PORT" -U "$RESTORE_USER" -d "$RESTORE_DB" \
            -f "$backup_file"
    fi
    
    unset PGPASSWORD
    
    log "===== RESTORE COMPLETE ====="
}

# 列出可用備份
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    echo ""
    echo "=== Full Backups ==="
    ls -lh "$BACKUP_DIR/full/" 2>/dev/null || echo "  (none)"
    echo ""
    echo "=== Incremental Backups ==="
    ls -lh "$BACKUP_DIR/incremental/" 2>/dev/null || echo "  (none)"
    echo ""
    echo "=== Remote Backups ==="
    ls -lh "$BACKUP_DIR/remote/" 2>/dev/null || echo "  (none)"
}

# 顯示使用說明
usage() {
    echo "Usage: $0 [restore <backup_file>|list]"
    echo ""
    echo "Commands:"
    echo "  restore <file> - Restore from backup file"
    echo "  list           - List available backups"
    echo ""
    echo "Examples:"
    echo "  $0 restore /backups/full/full_20260105_120000.sql.gz.enc"
    echo "  $0 list"
    echo ""
    echo "Environment Variables (Restore-specific):"
    echo "  RESTORE_POSTGRES_HOST     - Target host (default: POSTGRES_HOST)"
    echo "  RESTORE_POSTGRES_PORT     - Target port (default: POSTGRES_PORT)"
    echo "  RESTORE_POSTGRES_USERNAME - Target user (default: POSTGRES_USERNAME)"
    echo "  RESTORE_POSTGRES_PASSWORD - Target password (default: POSTGRES_PASSWORD)"
    echo "  RESTORE_POSTGRES_DATABASE - Target database (default: POSTGRES_DATABASE)"
    echo "  RESTORE_DROP_DATABASE     - Drop existing database (default: false)"
    echo "  RESTORE_CREATE_DATABASE   - Create database if not exists (default: true)"
    exit 1
}

# 主程式
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
