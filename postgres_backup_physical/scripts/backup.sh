#!/bin/sh
# ============================================================================
# PostgreSQL 物理備份腳本 (使用 pg_basebackup + WAL Archive)
#
# 這個腳本使用 PostgreSQL 官方提供的 pg_basebackup 工具進行物理備份，
# 配合 WAL (Write-Ahead Log) 歸檔實現真正的增量備份和 PITR (Point-in-Time Recovery)。
#
# 技術原理:
# - pg_basebackup: 建立資料庫的完整二進制副本 (Base Backup)
# - WAL Archive: PostgreSQL 自動將 WAL 檔案歸檔，記錄所有資料變更
# - PITR: 結合 Base Backup + WAL 重放，可還原到任意時間點
#
# 這是 AWS RDS、Google Cloud SQL、Azure Database 等企業級服務採用的備份方式。
#
# 使用場景:
# - 大型資料庫 (> 100GB) - 物理備份比邏輯備份快數倍
# - 需要 PITR - 可還原到任意時間點，最小化資料遺失
# - 生產環境 - RPO (Recovery Point Objective) 近乎零
#
# 參考文獻:
# - pg_basebackup: https://www.postgresql.org/docs/current/app-pgbasebackup.html
# - WAL 原理: https://www.postgresql.org/docs/current/wal-intro.html
# - PITR: https://www.postgresql.org/docs/current/continuous-archiving.html
#
# 支援功能: Base Backup / WAL Archive / 異地備份 / PITR / 加密
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
POSTGRES_WAL_DIR="${POSTGRES_WAL_DIR:-/postgres_backups/wal}"

# Base Backup 設定
BASE_BACKUP_RETENTION_DAYS="${BASE_BACKUP_RETENTION_DAYS:-7}"
BASE_BACKUP_FORMAT="${BASE_BACKUP_FORMAT:-tar}"
BASE_BACKUP_COMPRESSION="${BASE_BACKUP_COMPRESSION:-true}"

# 加密設定
BACKUP_ENCRYPTION_ENABLED="${BACKUP_ENCRYPTION_ENABLED:-false}"
BACKUP_ENCRYPTION_ALGORITHM="${BACKUP_ENCRYPTION_ALGORITHM:-aes-256-cbc}"

# WAL 設定
WAL_RETENTION_DAYS="${WAL_RETENTION_DAYS:-14}"
WAL_COMPRESSION="${WAL_COMPRESSION:-true}"
WAL_ENCRYPTION_ENABLED="${WAL_ENCRYPTION_ENABLED:-false}"

# 異地備份
REMOTE_BACKUP_ENABLED="${REMOTE_BACKUP_ENABLED:-false}"
REMOTE_BACKUP_RETENTION_DAYS="${REMOTE_BACKUP_RETENTION_DAYS:-90}"

# 連接模式: docker (透過 Docker 網路) 或 host (直接連接宿主機)
POSTGRES_CONNECTION_MODE="${POSTGRES_CONNECTION_MODE:-docker}"

# 目錄結構
BASE_BACKUP_DIR="$BACKUP_DIR/base"
WAL_BACKUP_DIR="$BACKUP_DIR/wal"
REMOTE_BACKUP_DIR="$BACKUP_DIR/remote"
LOG_DIR="$BACKUP_DIR/logs"

# 建立目錄
mkdir -p "$BASE_BACKUP_DIR" "$WAL_BACKUP_DIR" "$REMOTE_BACKUP_DIR" "$LOG_DIR"

# 時間戳記
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/backup_${TIMESTAMP}.log"

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 驗證必要配置
validate_config() {
    [ -z "$POSTGRES_PASSWORD" ] && error_exit "POSTGRES_PASSWORD is required"
    
    # 驗證加密配置
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
        -d "${POSTGRES_DATABASE:-postgres}" -c "SELECT 1;" >/dev/null 2>&1; then
        log "  Connection: OK"
        log "  Host: $POSTGRES_HOST:$POSTGRES_PORT"
        log "  Connection Mode: $POSTGRES_CONNECTION_MODE"
        unset PGPASSWORD
        return 0
    else
        log "  Connection: FAILED"
        unset PGPASSWORD
        return 1
    fi
}

# ============================================
# Base Backup (Physical Full Backup)
# 使用 pg_basebackup 建立完整的物理備份
# ============================================
backup_base() {
    log "===== BASE BACKUP START ====="
    validate_config
    
    local backup_name="base_${TIMESTAMP}"
    local backup_path="$BASE_BACKUP_DIR/$backup_name"
    
    log "Creating base backup: $backup_path"
    log "  Host: $POSTGRES_HOST:$POSTGRES_PORT"
    log "  Connection Mode: $POSTGRES_CONNECTION_MODE"
    log "  Format: $BASE_BACKUP_FORMAT"
    log "  Compression: $BASE_BACKUP_COMPRESSION"
    log "  Encryption: $BACKUP_ENCRYPTION_ENABLED"
    [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ] && log "  Encryption Algorithm: $BACKUP_ENCRYPTION_ALGORITHM"
    
    # 測試連接
    if ! test_connection; then
        error_exit "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
    fi
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # 建立備份目錄
    mkdir -p "$backup_path"
    
    # 構建 pg_basebackup 參數
    local pg_opts="-h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USERNAME"
    pg_opts="$pg_opts -D $backup_path"
    pg_opts="$pg_opts -Xs -P -c fast"
    pg_opts="$pg_opts --label=base_backup_$TIMESTAMP"
    
    if [ "$BASE_BACKUP_FORMAT" = "tar" ]; then
        pg_opts="$pg_opts -Ft"
        if [ "$BASE_BACKUP_COMPRESSION" = "true" ]; then
            pg_opts="$pg_opts -z"
        fi
    else
        pg_opts="$pg_opts -Fp"
    fi
    
    # 執行 pg_basebackup
    pg_basebackup $pg_opts
    
    local exit_code=$?
    unset PGPASSWORD
    
    if [ $exit_code -eq 0 ] && [ -d "$backup_path" ]; then
        local backup_size=$(du -sh "$backup_path" | cut -f1)
        log "Base backup completed successfully"
        log "  Path: $backup_path"
        log "  Size: $backup_size"
        
        # 如果啟用加密，對備份檔案進行加密
        if [ "$BACKUP_ENCRYPTION_ENABLED" = "true" ]; then
            log "Encrypting backup files..."
            
            for file in "$backup_path"/*.tar.gz "$backup_path"/*.tar; do
                if [ -f "$file" ]; then
                    log "  Encrypting: $(basename "$file")"
                    openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -salt -pbkdf2 \
                        -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
                        -in "$file" -out "${file}.enc"
                    rm -f "$file"
                fi
            done
            
            log "Encryption completed"
        fi
        
        # 記錄備份資訊
        cat > "$backup_path/backup_info" << EOF
BACKUP_NAME=$backup_name
BACKUP_TIME=$TIMESTAMP
BACKUP_TYPE=base
BACKUP_FORMAT=$BASE_BACKUP_FORMAT
BACKUP_COMPRESSION=$BASE_BACKUP_COMPRESSION
BACKUP_ENCRYPTION=$BACKUP_ENCRYPTION_ENABLED
ENCRYPTION_ALGORITHM=$BACKUP_ENCRYPTION_ALGORITHM
CONNECTION_MODE=$POSTGRES_CONNECTION_MODE
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_VERSION=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" -t -c "SELECT version();" 2>/dev/null | head -1 || echo "unknown")
EOF
        
        # 清理舊的 base backup
        log "Cleaning up base backups older than $BASE_BACKUP_RETENTION_DAYS days..."
        find "$BASE_BACKUP_DIR" -maxdepth 1 -type d -name "base_*" -mtime +$BASE_BACKUP_RETENTION_DAYS -exec rm -rf {} \;
        
        log "===== BASE BACKUP COMPLETE ====="
    else
        error_exit "Base backup failed"
    fi
}

# ============================================
# WAL Archive Sync
# 同步 WAL 歸檔檔案到本地備份目錄
# ============================================
backup_wal() {
    log "===== WAL ARCHIVE SYNC START ====="
    
    if [ ! -d "$POSTGRES_WAL_DIR" ]; then
        log "WARNING: PostgreSQL WAL directory not found: $POSTGRES_WAL_DIR"
        log "Make sure PostgreSQL is configured with archive_mode=on"
        return 1
    fi
    
    # 同步 WAL 檔案
    log "Syncing WAL files from $POSTGRES_WAL_DIR to $WAL_BACKUP_DIR"
    log "  WAL Compression: $WAL_COMPRESSION"
    log "  WAL Encryption: $WAL_ENCRYPTION_ENABLED"
    [ "$WAL_ENCRYPTION_ENABLED" = "true" ] && log "  Encryption Algorithm: $BACKUP_ENCRYPTION_ALGORITHM"
    
    local wal_count=0
    for wal_file in "$POSTGRES_WAL_DIR"/*; do
        if [ -f "$wal_file" ]; then
            local filename=$(basename "$wal_file")
            local dest_file="$WAL_BACKUP_DIR/$filename"
            
            # 檢查是否已存在 (考慮各種副檔名)
            if [ ! -f "$dest_file" ] && [ ! -f "${dest_file}.gz" ] && \
               [ ! -f "${dest_file}.enc" ] && [ ! -f "${dest_file}.gz.enc" ]; then
                
                if [ "$WAL_COMPRESSION" = "true" ] && [ "$WAL_ENCRYPTION_ENABLED" = "true" ]; then
                    # 壓縮 + 加密
                    gzip -c "$wal_file" | \
                        openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -salt -pbkdf2 \
                        -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
                        -out "${dest_file}.gz.enc"
                    log "Archived: $filename -> ${filename}.gz.enc"
                elif [ "$WAL_COMPRESSION" = "true" ]; then
                    # 僅壓縮
                    gzip -c "$wal_file" > "${dest_file}.gz"
                    log "Archived: $filename -> ${filename}.gz"
                elif [ "$WAL_ENCRYPTION_ENABLED" = "true" ]; then
                    # 僅加密
                    openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -salt -pbkdf2 \
                        -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
                        -in "$wal_file" -out "${dest_file}.enc"
                    log "Archived: $filename -> ${filename}.enc"
                else
                    # 原始複製
                    cp "$wal_file" "$dest_file"
                    log "Archived: $filename"
                fi
                wal_count=$((wal_count + 1))
            fi
        fi
    done
    
    log "Synced $wal_count new WAL files"
    
    # 清理舊的 WAL 備份
    log "Cleaning up WAL archives older than $WAL_RETENTION_DAYS days..."
    find "$WAL_BACKUP_DIR" -type f -mtime +$WAL_RETENTION_DAYS -delete
    
    log "===== WAL ARCHIVE SYNC COMPLETE ====="
}

# ============================================
# Switch WAL
# 強制切換 WAL 段以確保最新資料被歸檔
# ============================================
backup_switch() {
    log "===== WAL SWITCH START ====="
    validate_config
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    log "Forcing WAL segment switch..."
    local result=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "${POSTGRES_DATABASE:-postgres}" -t -c "SELECT pg_switch_wal();" 2>/dev/null)
    
    unset PGPASSWORD
    
    log "WAL switched: $result"
    
    # 等待 WAL 歸檔
    sleep 2
    
    # 同步新的 WAL
    backup_wal
    
    log "===== WAL SWITCH COMPLETE ====="
}

# ============================================
# 異地備份
# 傳送 Base Backup 和 WAL 到遠端
# ============================================
backup_remote() {
    log "===== REMOTE BACKUP START ====="
    validate_config
    
    if [ "$REMOTE_BACKUP_ENABLED" != "true" ]; then
        error_exit "Remote backup is not enabled. Set REMOTE_BACKUP_ENABLED=true"
    fi
    
    [ -z "$REMOTE_BACKUP_HOST" ] && error_exit "REMOTE_BACKUP_HOST is required"
    [ -z "$REMOTE_BACKUP_USER" ] && error_exit "REMOTE_BACKUP_USER is required"
    [ -z "$REMOTE_BACKUP_PATH" ] && error_exit "REMOTE_BACKUP_PATH is required"
    
    # 找到最新的 Base Backup
    local latest_base=$(ls -dt "$BASE_BACKUP_DIR"/base_* 2>/dev/null | head -1)
    
    if [ -z "$latest_base" ]; then
        log "No base backup found, creating one first..."
        backup_base
        latest_base=$(ls -dt "$BASE_BACKUP_DIR"/base_* 2>/dev/null | head -1)
    fi
    
    local backup_name=$(basename "$latest_base")
    local remote_backup_name="remote_${TIMESTAMP}"
    local local_archive="$REMOTE_BACKUP_DIR/${remote_backup_name}.tar.gz"
    
    log "Creating remote backup archive..."
    log "  Base Backup: $backup_name"
    log "  Archive: $local_archive"
    
    # 打包 Base Backup 和 WAL
    tar -czf "$local_archive" -C "$BACKUP_DIR" \
        "base/$backup_name" \
        "wal/"
    
    local archive_size=$(du -h "$local_archive" | cut -f1)
    log "Archive created: $archive_size"
    
    # 傳送到遠端
    log "Transferring to remote: $REMOTE_BACKUP_USER@$REMOTE_BACKUP_HOST:$REMOTE_BACKUP_PATH"
    
    local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    [ -n "$REMOTE_BACKUP_SSH_KEY" ] && [ -f "$REMOTE_BACKUP_SSH_KEY" ] && ssh_opts="$ssh_opts -i $REMOTE_BACKUP_SSH_KEY"
    [ -n "$REMOTE_BACKUP_PORT" ] && ssh_opts="$ssh_opts -P $REMOTE_BACKUP_PORT"
    
    scp $ssh_opts "$local_archive" "$REMOTE_BACKUP_USER@$REMOTE_BACKUP_HOST:$REMOTE_BACKUP_PATH/"
    
    if [ $? -eq 0 ]; then
        log "Remote transfer completed successfully"
    else
        error_exit "Remote transfer failed"
    fi
    
    # 清理過期備份
    log "Cleaning up remote archives older than $REMOTE_BACKUP_RETENTION_DAYS days..."
    find "$REMOTE_BACKUP_DIR" -name "remote_*.tar.gz" -mtime +$REMOTE_BACKUP_RETENTION_DAYS -delete
    
    log "===== REMOTE BACKUP COMPLETE ====="
}

# ============================================
# 列出可用備份
# ============================================
list_backups() {
    echo "===== AVAILABLE BACKUPS ====="
    echo ""
    echo "=== Base Backups (Physical) ==="
    if [ -d "$BASE_BACKUP_DIR" ]; then
        for backup_dir in "$BASE_BACKUP_DIR"/base_*; do
            if [ -d "$backup_dir" ]; then
                local name=$(basename "$backup_dir")
                local size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
                echo "  $name - $size"
            fi
        done
    else
        echo "  (none)"
    fi
    
    echo ""
    echo "=== WAL Archives ==="
    if [ -d "$WAL_BACKUP_DIR" ]; then
        local wal_count=$(ls "$WAL_BACKUP_DIR" 2>/dev/null | wc -l | tr -d ' ')
        local wal_size=$(du -sh "$WAL_BACKUP_DIR" 2>/dev/null | cut -f1)
        echo "  Total WAL files: $wal_count"
        echo "  Total size: $wal_size"
        
        if [ "$wal_count" -gt 0 ]; then
            echo "  Oldest: $(ls -t "$WAL_BACKUP_DIR" 2>/dev/null | tail -1)"
            echo "  Newest: $(ls -t "$WAL_BACKUP_DIR" 2>/dev/null | head -1)"
        fi
    else
        echo "  (none)"
    fi
    
    echo ""
    echo "=== Remote Backups ==="
    ls -lh "$REMOTE_BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  (none)"
}

# ============================================
# 顯示備份狀態
# ============================================
backup_status() {
    log "===== BACKUP STATUS ====="
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    echo ""
    echo "=== PostgreSQL Connection ==="
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "${POSTGRES_DATABASE:-postgres}" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "  Status: Connected ✓"
        echo "  Host: $POSTGRES_HOST:$POSTGRES_PORT"
    else
        echo "  Status: Connection Failed ✗"
    fi
    
    echo ""
    echo "=== WAL Configuration ==="
    local wal_level=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "${POSTGRES_DATABASE:-postgres}" -t -c "SHOW wal_level;" 2>/dev/null | tr -d ' ')
    local archive_mode=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "${POSTGRES_DATABASE:-postgres}" -t -c "SHOW archive_mode;" 2>/dev/null | tr -d ' ')
    local archive_command=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
        -d "${POSTGRES_DATABASE:-postgres}" -t -c "SHOW archive_command;" 2>/dev/null | tr -d ' ')
    
    echo "  wal_level: $wal_level"
    echo "  archive_mode: $archive_mode"
    echo "  archive_command: $archive_command"
    
    if [ "$wal_level" != "replica" ] && [ "$wal_level" != "logical" ]; then
        echo "  WARNING: wal_level should be 'replica' or 'logical' for physical backup"
    fi
    if [ "$archive_mode" != "on" ]; then
        echo "  WARNING: archive_mode should be 'on' for WAL archiving"
    fi
    
    unset PGPASSWORD
    
    echo ""
    echo "=== Storage ==="
    echo "  Base Backup Dir: $BASE_BACKUP_DIR"
    echo "  WAL Archive Dir: $WAL_BACKUP_DIR"
    echo "  Disk Usage:"
    df -h "$BACKUP_DIR" 2>/dev/null | tail -1 | awk '{print "    Total: "$2", Used: "$3", Available: "$4}'
    
    list_backups
}

# 顯示使用說明
usage() {
    echo "Usage: $0 [base|wal|switch|remote|list|status]"
    echo ""
    echo "Commands:"
    echo "  base    - Create base backup (physical full backup)"
    echo "  wal     - Sync WAL archives (incremental)"
    echo "  switch  - Force WAL switch and sync"
    echo "  remote  - Create and transfer remote backup"
    echo "  list    - List available backups"
    echo "  status  - Show backup system status"
    echo ""
    echo "Recommended Schedule:"
    echo "  Weekly:  base   - Full physical backup"
    echo "  Hourly:  switch - WAL switch + sync (true incremental)"
    echo "  Monthly: remote - Offsite backup"
    exit 1
}

# 主程式
case "${1:-}" in
    base)
        backup_base
        ;;
    wal)
        backup_wal
        ;;
    switch)
        backup_switch
        ;;
    remote)
        backup_remote
        ;;
    list)
        list_backups
        ;;
    status)
        backup_status
        ;;
    *)
        usage
        ;;
esac
