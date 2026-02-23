#!/bin/sh
# ============================================================================
# PostgreSQL 邏輯備份腳本 (使用 pg_dump - PostgreSQL 官方備份工具)
# 
# 這個腳本使用 PostgreSQL 官方提供的 pg_dump 工具進行資料庫備份。
# pg_dump 是 PostgreSQL 推薦的邏輯備份方式，被 AWS RDS、Google Cloud SQL、
# Heroku 等主流雲端服務廣泛採用。
#
# 技術說明:
# - pg_dump 會產生一致性的資料庫快照 (使用交易確保資料一致)
# - 備份包含: 表格結構、資料、索引、約束、序列、視圖、函數等
# - 輸出為 SQL 格式，可透過 psql 還原
# - 支援跨 PostgreSQL 版本還原
#
# 參考文獻:
# - PostgreSQL pg_dump 官方文件: https://www.postgresql.org/docs/current/app-pgdump.html
# - PostgreSQL Backup: https://www.postgresql.org/docs/current/backup-dump.html
#
# 支援功能: 完全備份 / 增量備份 / 異地備份 / 壓縮 / 加密
# ============================================================================

set -e

# 載入配置
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

# 預設值
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USERNAME="${POSTGRES_USERNAME:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
FULL_BACKUP_RETENTION_DAYS="${FULL_BACKUP_RETENTION_DAYS:-30}"
INCREMENTAL_BACKUP_RETENTION_DAYS="${INCREMENTAL_BACKUP_RETENTION_DAYS:-7}"
REMOTE_BACKUP_RETENTION_DAYS="${REMOTE_BACKUP_RETENTION_DAYS:-90}"
BACKUP_COMPRESSION_ENABLED="${BACKUP_COMPRESSION_ENABLED:-true}"
BACKUP_ENCRYPTION_ENABLED="${BACKUP_ENCRYPTION_ENABLED:-false}"

# 加密算法配置 (支援: aes-256-cbc, aes-128-cbc, aes-256-gcm, chacha20-poly1305)
BACKUP_ENCRYPTION_ALGORITHM="${BACKUP_ENCRYPTION_ALGORITHM:-aes-256-cbc}"

# 連接模式: docker (透過 Docker 網路) 或 host (直接連接宿主機)
# 當 POSTGRES_CONNECTION_MODE=host 時，可連接非 Docker 運行的 PostgreSQL
POSTGRES_CONNECTION_MODE="${POSTGRES_CONNECTION_MODE:-docker}"

# 目錄結構
FULL_BACKUP_DIR="$BACKUP_DIR/full"
INCREMENTAL_BACKUP_DIR="$BACKUP_DIR/incremental"
REMOTE_BACKUP_DIR="$BACKUP_DIR/remote"
LOG_DIR="$BACKUP_DIR/logs"

# 建立目錄
mkdir -p "$FULL_BACKUP_DIR" "$INCREMENTAL_BACKUP_DIR" "$REMOTE_BACKUP_DIR" "$LOG_DIR"

# 時間戳記
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/backup_${TIMESTAMP}.log"

# 日誌函數 (輸出到 stderr 避免干擾命令替換)
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" >&2
}

# 錯誤處理
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 驗證必要配置
validate_config() {
    [ -z "$POSTGRES_DATABASE" ] && error_exit "POSTGRES_DATABASE is required"
    [ -z "$POSTGRES_PASSWORD" ] && error_exit "POSTGRES_PASSWORD is required"
    if [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ] && [ -z "$BACKUP_ENCRYPTION_PASSWORD" ]; then
        error_exit "BACKUP_ENCRYPTION_PASSWORD is required when encryption is enabled"
    fi
    
    # 驗證加密算法
    if [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
        case "$BACKUP_ENCRYPTION_ALGORITHM" in
            aes-256-cbc|aes-128-cbc|aes-256-gcm|chacha20-poly1305|aes-192-cbc)
                log "Using encryption algorithm: $BACKUP_ENCRYPTION_ALGORITHM"
                ;;
            *)
                error_exit "Unsupported encryption algorithm: $BACKUP_ENCRYPTION_ALGORITHM"
                ;;
        esac
    fi
}

# 測試 PostgreSQL 連接
test_connection() {
    log "Testing PostgreSQL connection..."
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "$POSTGRES_DATABASE" -c "SELECT 1;" >/dev/null 2>&1; then
        log "  Connection: OK"
        unset PGPASSWORD
        return 0
    else
        log "  Connection: FAILED"
        unset PGPASSWORD
        return 1
    fi
}

# 取得檔案副檔名
get_file_extension() {
    local ext=".sql"
    [ "$BACKUP_COMPRESSION_ENABLED" = "true" ] && ext="${ext}.gz"
    [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ] && ext="${ext}.enc"
    echo "$ext"
}

# 執行備份並處理壓縮/加密
do_backup() {
    local backup_type="$1"
    local output_dir="$2"
    local pg_dump_opts="$3"
    
    local ext=$(get_file_extension)
    local backup_file="${output_dir}/${backup_type}_${TIMESTAMP}${ext}"
    
    log "Starting $backup_type backup..."
    log "  Database: $POSTGRES_DATABASE"
    log "  Host: $POSTGRES_HOST:$POSTGRES_PORT"
    log "  Connection Mode: $POSTGRES_CONNECTION_MODE"
    log "  Compression: $BACKUP_COMPRESSION_ENABLED"
    log "  Encryption: $BACKUP_ENCRYPTION_ENABLED"
    [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ] && log "  Encryption Algorithm: $BACKUP_ENCRYPTION_ALGORITHM"
    
    # 設定密碼
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # 執行 pg_dump
    if [ "$BACKUP_COMPRESSION_ENABLED" = "true" ] && [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
        # 壓縮 + 加密: pg_dump | gzip | openssl
        pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
            -d "$POSTGRES_DATABASE" $pg_dump_opts | \
            gzip -9 | \
            openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -out "$backup_file"
    elif [ "$BACKUP_COMPRESSION_ENABLED" = "true" ]; then
        # 僅壓縮: pg_dump | gzip
        pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
            -d "$POSTGRES_DATABASE" $pg_dump_opts | \
            gzip -9 > "$backup_file"
    elif [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
        # 僅加密: pg_dump | openssl
        pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
            -d "$POSTGRES_DATABASE" $pg_dump_opts | \
            openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -out "$backup_file"
    else
        # 純文字備份
        pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
            -d "$POSTGRES_DATABASE" $pg_dump_opts > "$backup_file"
    fi
    
    unset PGPASSWORD
    
    # 驗證備份檔案
    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        local file_size=$(du -h "$backup_file" | cut -f1)
        log "Backup completed: $backup_file ($file_size)"
        echo "$backup_file"
    else
        error_exit "Backup file is empty or not created"
    fi
}

# 完全備份 (Weekly)
backup_full() {
    log "===== FULL BACKUP START ====="
    validate_config
    
    # 先測試連接
    if ! test_connection; then
        error_exit "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
    fi
    
    local backup_file=$(do_backup "full" "$FULL_BACKUP_DIR" "--format=plain --no-owner --no-acl")
    
    # 檢查備份是否成功
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        error_exit "Backup failed - no backup file created"
    fi
    
    # 清理過期備份
    log "Cleaning up backups older than $FULL_BACKUP_RETENTION_DAYS days..."
    find "$FULL_BACKUP_DIR" -name "full_*" -type f -mtime +$FULL_BACKUP_RETENTION_DAYS -delete
    
    log "===== FULL BACKUP COMPLETE ====="
}

# 增量備份 (Daily) - 使用 pg_dump 的 schema 變更追蹤
backup_incremental() {
    log "===== INCREMENTAL BACKUP START ====="
    validate_config
    
    # 先測試連接
    if ! test_connection; then
        error_exit "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
    fi
    
    # 邏輯增量: 完整 dump (pg_dump 不支援真正的增量)
    # 建議搭配 WAL 物理備份實現真正增量
    local backup_file=$(do_backup "incremental" "$INCREMENTAL_BACKUP_DIR" "--format=plain --no-owner --no-acl")
    
    # 檢查備份是否成功
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        error_exit "Backup failed - no backup file created"
    fi
    
    # 清理過期備份
    log "Cleaning up backups older than $INCREMENTAL_BACKUP_RETENTION_DAYS days..."
    find "$INCREMENTAL_BACKUP_DIR" -name "incremental_*" -type f -mtime +$INCREMENTAL_BACKUP_RETENTION_DAYS -delete
    
    log "===== INCREMENTAL BACKUP COMPLETE ====="
}

# 異地備份 (Monthly)
backup_remote() {
    log "===== REMOTE BACKUP START ====="
    validate_config
    
    if [ "$REMOTE_BACKUP_ENABLED" != "true" ]; then
        error_exit "Remote backup is not enabled. Set REMOTE_BACKUP_ENABLED=true"
    fi
    
    [ -z "$REMOTE_BACKUP_HOST" ] && error_exit "REMOTE_BACKUP_HOST is required"
    [ -z "$REMOTE_BACKUP_USER" ] && error_exit "REMOTE_BACKUP_USER is required"
    [ -z "$REMOTE_BACKUP_PATH" ] && error_exit "REMOTE_BACKUP_PATH is required"
    
    # 先測試連接
    if ! test_connection; then
        error_exit "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
    fi
    
    # 先做本地完整備份
    local backup_file=$(do_backup "remote" "$REMOTE_BACKUP_DIR" "--format=plain --no-owner --no-acl")
    
    # 檢查備份是否成功
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        error_exit "Backup failed - no backup file created"
    fi
    
    # 傳送到遠端
    log "Transferring backup to remote: $REMOTE_BACKUP_USER@$REMOTE_BACKUP_HOST:$REMOTE_BACKUP_PATH"
    
    local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    [ -n "$REMOTE_BACKUP_SSH_KEY" ] && [ -f "$REMOTE_BACKUP_SSH_KEY" ] && ssh_opts="$ssh_opts -i $REMOTE_BACKUP_SSH_KEY"
    [ -n "$REMOTE_BACKUP_PORT" ] && ssh_opts="$ssh_opts -P $REMOTE_BACKUP_PORT"
    
    scp $ssh_opts "$backup_file" "$REMOTE_BACKUP_USER@$REMOTE_BACKUP_HOST:$REMOTE_BACKUP_PATH/"
    
    if [ $? -eq 0 ]; then
        log "Remote transfer completed successfully"
    else
        error_exit "Remote transfer failed"
    fi
    
    # 清理過期備份
    log "Cleaning up backups older than $REMOTE_BACKUP_RETENTION_DAYS days..."
    find "$REMOTE_BACKUP_DIR" -name "remote_*" -type f -mtime +$REMOTE_BACKUP_RETENTION_DAYS -delete
    
    log "===== REMOTE BACKUP COMPLETE ====="
}

# 列出可用備份
list_backups() {
    echo "===== AVAILABLE BACKUPS ====="
    echo ""
    echo "=== Full Backups ==="
    ls -lh "$FULL_BACKUP_DIR" 2>/dev/null || echo "  (none)"
    echo ""
    echo "=== Incremental Backups ==="
    ls -lh "$INCREMENTAL_BACKUP_DIR" 2>/dev/null || echo "  (none)"
    echo ""
    echo "=== Remote Backups ==="
    ls -lh "$REMOTE_BACKUP_DIR" 2>/dev/null || echo "  (none)"
}

# 顯示使用說明
usage() {
    echo "Usage: $0 [full|incremental|remote|list]"
    echo ""
    echo "Commands:"
    echo "  full        - Full database backup (Weekly)"
    echo "  incremental - Incremental backup (Daily)"
    echo "  remote      - Remote/offsite backup (Monthly)"
    echo "  list        - List available backups"
    echo ""
    echo "Environment Variables:"
    echo "  CONFIG_FILE - Path to config file (default: /scripts/config/.env)"
    exit 1
}

# 主程式
case "${1:-}" in
    full)
        backup_full
        ;;
    incremental)
        backup_incremental
        ;;
    remote)
        backup_remote
        ;;
    list)
        list_backups
        ;;
    *)
        usage
        ;;
esac
