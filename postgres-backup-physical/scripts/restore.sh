#!/bin/sh
# ============================================
# PostgreSQL 物理還原腳本 (PITR)
# 支援: Base Backup + WAL Replay
# ============================================

set -e

# 載入配置
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

# 預設值
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BASE_BACKUP_DIR="$BACKUP_DIR/base"
WAL_BACKUP_DIR="$BACKUP_DIR/wal"
RESTORE_STAGING_DIR="${RESTORE_STAGING_DIR:-$BACKUP_DIR/restore_staging}"
LOG_DIR="$BACKUP_DIR/logs"

# 加密配置
BACKUP_ENCRYPTION_ENABLED="${BACKUP_ENCRYPTION_ENABLED:-false}"
BACKUP_ENCRYPTION_ALGORITHM="${BACKUP_ENCRYPTION_ALGORITHM:-aes-256-cbc}"

mkdir -p "$LOG_DIR" "$RESTORE_STAGING_DIR"

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

# ============================================
# 列出可用的 Base Backups
# ============================================
list_backups() {
    echo "===== AVAILABLE BACKUPS ====="
    echo ""
    echo "=== Base Backups ==="
    
    if [ ! -d "$BASE_BACKUP_DIR" ]; then
        echo "  (no base backups found)"
    else
        local i=1
        for backup_dir in "$BASE_BACKUP_DIR"/base_*; do
            if [ -d "$backup_dir" ]; then
                local name=$(basename "$backup_dir")
                local size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
                local timestamp=$(echo "$name" | sed 's/base_//')
                local date=$(echo "$timestamp" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
                echo "  [$i] $name"
                echo "      Date: $date"
                echo "      Size: $size"
                echo ""
                i=$((i + 1))
            fi
        done
    fi
    
    echo "=== WAL Archive Range ==="
    if [ ! -d "$WAL_BACKUP_DIR" ]; then
        echo "  (no WAL archives found)"
    else
        local wal_count=$(ls "$WAL_BACKUP_DIR" 2>/dev/null | wc -l | tr -d ' ')
        
        if [ "$wal_count" -eq 0 ]; then
            echo "  (no WAL archives found)"
        else
            local oldest=$(ls -t "$WAL_BACKUP_DIR" 2>/dev/null | tail -1)
            local newest=$(ls -t "$WAL_BACKUP_DIR" 2>/dev/null | head -1)
            local total_size=$(du -sh "$WAL_BACKUP_DIR" 2>/dev/null | cut -f1)
            
            echo "  Total WAL files: $wal_count"
            echo "  Total size: $total_size"
            echo "  Oldest: $oldest"
            echo "  Newest: $newest"
        fi
    fi
}

# ============================================
# 準備還原環境
# ============================================
prepare_restore() {
    local base_backup="$1"
    local restore_target="$2"
    
    log "===== PREPARE RESTORE ====="
    log "Base Backup: $base_backup"
    log "Restore Target: $restore_target"
    
    if [ ! -d "$base_backup" ]; then
        error_exit "Base backup not found: $base_backup"
    fi
    
    # 讀取備份資訊以檢測加密
    local is_encrypted="false"
    if [ -f "$base_backup/backup_info" ]; then
        is_encrypted=$(grep "^BACKUP_ENCRYPTION=" "$base_backup/backup_info" | cut -d= -f2 || echo "false")
    fi
    
    # 檢測是否有加密檔案
    if [ -f "$base_backup/base.tar.gz.enc" ] || [ -f "$base_backup/base.tar.enc" ]; then
        is_encrypted="true"
    fi
    
    log "  Encrypted: $is_encrypted"
    
    if [ "$is_encrypted" = "true" ] && [ -z "$BACKUP_ENCRYPTION_PASSWORD" ]; then
        error_exit "BACKUP_ENCRYPTION_PASSWORD is required for encrypted backups"
    fi
    
    # 清理暫存目錄
    rm -rf "$restore_target"
    mkdir -p "$restore_target"
    
    # 解壓縮 base backup
    log "Extracting base backup..."
    
    if [ -f "$base_backup/base.tar.gz.enc" ]; then
        # 解密 + 解壓縮
        log "Decrypting and extracting base.tar.gz.enc"
        openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -d -pbkdf2 \
            -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$base_backup/base.tar.gz.enc" | \
            tar -xzf - -C "$restore_target"
    elif [ -f "$base_backup/base.tar.enc" ]; then
        # 僅解密
        log "Decrypting and extracting base.tar.enc"
        openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -d -pbkdf2 \
            -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$base_backup/base.tar.enc" | \
            tar -xf - -C "$restore_target"
    elif [ -f "$base_backup/base.tar.gz" ]; then
        tar -xzf "$base_backup/base.tar.gz" -C "$restore_target"
        log "Extracted base.tar.gz"
    elif [ -f "$base_backup/base.tar" ]; then
        tar -xf "$base_backup/base.tar" -C "$restore_target"
        log "Extracted base.tar"
    else
        # Plain format - copy directory
        cp -r "$base_backup"/* "$restore_target/"
        log "Copied plain format backup"
    fi
    
    # 解壓縮 pg_wal (如果存在)
    if [ -f "$base_backup/pg_wal.tar.gz.enc" ]; then
        mkdir -p "$restore_target/pg_wal"
        openssl enc -$BACKUP_ENCRYPTION_ALGORITHM -d -pbkdf2 \
            -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" \
            -in "$base_backup/pg_wal.tar.gz.enc" | \
            tar -xzf - -C "$restore_target/pg_wal"
        log "Decrypted and extracted pg_wal.tar.gz.enc"
    elif [ -f "$base_backup/pg_wal.tar.gz" ]; then
        mkdir -p "$restore_target/pg_wal"
        tar -xzf "$base_backup/pg_wal.tar.gz" -C "$restore_target/pg_wal"
        log "Extracted pg_wal.tar.gz"
    elif [ -f "$base_backup/pg_wal.tar" ]; then
        mkdir -p "$restore_target/pg_wal"
        tar -xf "$base_backup/pg_wal.tar" -C "$restore_target/pg_wal"
        log "Extracted pg_wal.tar"
    fi
    
    log "Base backup prepared in: $restore_target"
}

# ============================================
# 配置 PITR
# ============================================
configure_pitr() {
    local data_dir="$1"
    local target_time="$2"
    local wal_restore_dir="$3"
    
    log "===== CONFIGURE PITR ====="
    log "Data Dir: $data_dir"
    log "Target Time: ${target_time:-latest}"
    log "WAL Restore Dir: $wal_restore_dir"
    
    # 建立 recovery.signal (PostgreSQL 12+)
    touch "$data_dir/recovery.signal"
    log "Created recovery.signal"
    
    # 構建 restore_command
    local restore_cmd="cp $wal_restore_dir/%f %p || gunzip -c $wal_restore_dir/%f.gz > %p"
    
    # 建立 postgresql.auto.conf 配置
    cat > "$data_dir/postgresql.auto.conf" << EOF
# PITR Recovery Configuration
# Generated: $(date)

# WAL 還原命令
restore_command = '$restore_cmd'

# 還原目標
EOF
    
    if [ -n "$target_time" ]; then
        echo "recovery_target_time = '$target_time'" >> "$data_dir/postgresql.auto.conf"
        log "Set recovery target time: $target_time"
    else
        echo "recovery_target = 'immediate'" >> "$data_dir/postgresql.auto.conf"
        log "Set recovery target: immediate (latest)"
    fi
    
    # 還原後動作
    echo "recovery_target_action = 'promote'" >> "$data_dir/postgresql.auto.conf"
    
    log "PITR configuration written to postgresql.auto.conf"
}

# ============================================
# 執行 PITR 還原
# ============================================
do_pitr_restore() {
    local base_backup_name="$1"
    local target_time="$2"
    
    log "===== PITR RESTORE START ====="
    
    local base_backup_path="$BASE_BACKUP_DIR/$base_backup_name"
    
    if [ ! -d "$base_backup_path" ]; then
        error_exit "Base backup not found: $base_backup_path"
    fi
    
    log "Base Backup: $base_backup_name"
    log "Target Time: ${target_time:-latest (all available WAL)}"
    
    # 準備還原目錄
    local restore_data_dir="$RESTORE_STAGING_DIR/pgdata"
    prepare_restore "$base_backup_path" "$restore_data_dir"
    
    # 準備 WAL 還原目錄
    local wal_restore_dir="$RESTORE_STAGING_DIR/wal_restore"
    rm -rf "$wal_restore_dir"
    mkdir -p "$wal_restore_dir"
    
    # 複製所有 WAL 檔案到還原目錄
    log "Preparing WAL files for replay..."
    local wal_count=0
    for wal_file in "$WAL_BACKUP_DIR"/*; do
        if [ -f "$wal_file" ]; then
            cp "$wal_file" "$wal_restore_dir/"
            wal_count=$((wal_count + 1))
        fi
    done
    log "Prepared $wal_count WAL files for replay"
    
    # 配置 PITR
    configure_pitr "$restore_data_dir" "$target_time" "$wal_restore_dir"
    
    log ""
    log "===== RESTORE PREPARED ====="
    log ""
    log "Restore data directory: $restore_data_dir"
    log "WAL restore directory: $wal_restore_dir"
    log ""
    log "To complete the restore:"
    log "1. Stop the target PostgreSQL server"
    log "2. Backup/remove the existing data directory"
    log "3. Copy $restore_data_dir to the target data directory"
    log "4. Ensure proper ownership (postgres:postgres)"
    log "5. Start PostgreSQL - it will automatically replay WAL and recover"
    log ""
    log "Example commands:"
    log "  docker stop postgres"
    log "  docker cp $restore_data_dir postgres:/var/lib/postgresql/data_restore"
    log "  docker exec postgres mv /var/lib/postgresql/data /var/lib/postgresql/data_old"
    log "  docker exec postgres mv /var/lib/postgresql/data_restore /var/lib/postgresql/data"
    log "  docker exec postgres chown -R postgres:postgres /var/lib/postgresql/data"
    log "  docker start postgres"
    log ""
    log "===== PITR RESTORE PREPARATION COMPLETE ====="
}

# ============================================
# 還原到最新狀態
# ============================================
do_prepare_restore() {
    local base_backup_name="$1"
    do_pitr_restore "$base_backup_name" ""
}

# ============================================
# 驗證備份完整性
# ============================================
verify_backup() {
    local base_backup_name="$1"
    
    log "===== VERIFY BACKUP ====="
    
    local base_backup_path="$BASE_BACKUP_DIR/$base_backup_name"
    
    if [ ! -d "$base_backup_path" ]; then
        error_exit "Base backup not found: $base_backup_path"
    fi
    
    echo ""
    echo "Verifying: $base_backup_name"
    echo ""
    
    # 檢查必要檔案
    echo "=== Backup Files ==="
    local has_base=false
    
    if [ -f "$base_backup_path/base.tar.gz" ]; then
        local size=$(du -h "$base_backup_path/base.tar.gz" | cut -f1)
        echo "  ✓ base.tar.gz ($size)"
        has_base=true
        
        # 驗證壓縮檔完整性
        if gzip -t "$base_backup_path/base.tar.gz" 2>/dev/null; then
            echo "    Integrity: OK"
        else
            echo "    Integrity: FAILED"
        fi
    elif [ -f "$base_backup_path/base.tar" ]; then
        local size=$(du -h "$base_backup_path/base.tar" | cut -f1)
        echo "  ✓ base.tar ($size)"
        has_base=true
    fi
    
    if [ "$has_base" = "false" ]; then
        echo "  ✗ base backup file (missing)"
    fi
    
    # 檢查 pg_wal
    echo ""
    echo "=== WAL Files ==="
    if [ -f "$base_backup_path/pg_wal.tar.gz" ]; then
        local size=$(du -h "$base_backup_path/pg_wal.tar.gz" | cut -f1)
        echo "  ✓ pg_wal.tar.gz ($size)"
    elif [ -f "$base_backup_path/pg_wal.tar" ]; then
        local size=$(du -h "$base_backup_path/pg_wal.tar" | cut -f1)
        echo "  ✓ pg_wal.tar ($size)"
    else
        echo "  - pg_wal (not included in base backup)"
    fi
    
    # 檢查備份資訊
    if [ -f "$base_backup_path/backup_info" ]; then
        echo ""
        echo "=== Backup Info ==="
        cat "$base_backup_path/backup_info" | sed 's/^/  /'
    fi
    
    # 檢查 WAL 歸檔
    echo ""
    echo "=== WAL Archives ==="
    local wal_count=$(ls "$WAL_BACKUP_DIR" 2>/dev/null | wc -l | tr -d ' ')
    echo "  Available WAL files: $wal_count"
    
    echo ""
    log "===== VERIFICATION COMPLETE ====="
}

# 顯示使用說明
usage() {
    echo "Usage: $0 [list|prepare|pitr|verify] [options]"
    echo ""
    echo "Commands:"
    echo "  list                       - List available base backups and WAL range"
    echo "  prepare <base_name>        - Prepare PITR restore to latest"
    echo "  pitr <base_name> <time>    - Prepare PITR restore to specific time"
    echo "  verify <base_name>         - Verify backup integrity"
    echo ""
    echo "Time Format for PITR:"
    echo "  '2026-01-10 14:30:00'      - Restore to specific timestamp"
    echo "  '2026-01-10 14:30:00+08'   - With timezone"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 prepare base_20260110_120000"
    echo "  $0 pitr base_20260110_120000 '2026-01-10 15:30:00'"
    echo "  $0 verify base_20260110_120000"
    exit 1
}

# 主程式
case "${1:-}" in
    list)
        list_backups
        ;;
    prepare)
        [ -z "$2" ] && error_exit "Base backup name is required"
        do_prepare_restore "$2"
        ;;
    pitr)
        [ -z "$2" ] && error_exit "Base backup name is required"
        [ -z "$3" ] && error_exit "Target time is required"
        do_pitr_restore "$2" "$3"
        ;;
    verify)
        [ -z "$2" ] && error_exit "Base backup name is required"
        verify_backup "$2"
        ;;
    *)
        usage
        ;;
esac
