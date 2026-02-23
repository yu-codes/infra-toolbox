#!/bin/bash

# ============================================================
# PostgreSQL 自動化備份腳本（含自動刪舊機制）
# ============================================================
# 功能：
#   1. 週全量備份（完整資料庫備份）
#   2. 日全量備份（每日完整備份）
#   3. 月異地備份
#   4. 自動刪除過期備份與日誌
# ============================================================

set -e

# 載入環境變數
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/backup.env"

# 載入加密工具函數
source "$SCRIPT_DIR/crypto_utils.sh"

# 日誌函數
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# 檢查 pg_dump/pg_dumpall 是否安裝
if ! command -v pg_dump &> /dev/null; then
    log_error "pg_dump 未安裝，請先安裝 PostgreSQL 客戶端工具"
    exit 1
fi

if ! command -v pg_dumpall &> /dev/null; then
    log_error "pg_dumpall 未安裝，請先安裝 PostgreSQL 客戶端工具"
    exit 1
fi

# 檢查加密與壓縮工具
if ! check_crypto_tools "$ENCRYPTION_METHOD" "$COMPRESSION_TYPE"; then
    log_error "加密或壓縮工具未安裝"
    exit 1
fi

# 建立必要目錄
mkdir -p "$FULL_DIR" "$DAILY_DIR" "$OFFSITE_DIR" "$(dirname "$LOG_FILE")"

# 設定 PostgreSQL 連線環境變數
export PGHOST="$PG_HOST"
export PGPORT="$PG_PORT"
export PGUSER="$PG_USER"
export PGPASSWORD="$PG_PASSWORD"

# 測試資料庫連線
log_info "測試資料庫連線..."
if ! psql -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    log_error "無法連線至 PostgreSQL: $PG_HOST:$PG_PORT"
    exit 1
fi

DAY_OF_WEEK=$(date +%w)
DAY_OF_MONTH=$(date +%d)
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DATE_ONLY=$(date '+%Y%m%d')

log_info "========== 開始執行備份 =========="

# ============================================================
# 1. 週全量備份（每週一次）- 所有資料庫 + 全局對象
# ============================================================
if [ "$ENABLE_FULL_BACKUP" = "true" ] && [ "$DAY_OF_WEEK" -eq "$FULL_BACKUP_DAY" ]; then
    log_info "執行每週完整備份（所有資料庫）..."
    
    FULL_BACKUP_DIR="$FULL_DIR/$DATE_ONLY"
    mkdir -p "$FULL_BACKUP_DIR"
    
    # 備份所有資料庫 + 全局對象（角色、表空間等）
    BACKUP_FILE="$FULL_BACKUP_DIR/full_backup_${TIMESTAMP}.sql"
    
    if pg_dumpall --clean --if-exists > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
        # 壓縮並加密備份檔案
        BACKUP_FILE=$(compress_and_encrypt "$BACKUP_FILE")
        if [ $? -eq 0 ]; then
            log_info "週全量備份完成: $BACKUP_FILE"
            # 計算檔案大小
            BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
            log_info "備份檔案大小: $BACKUP_SIZE"
        else
            log_error "壓縮或加密失敗"
        fi
    else
        log_error "週全量備份失敗"
    fi
fi

# ============================================================
# 2. 日全量備份（每日）- 個別資料庫
# ============================================================
if [ "$ENABLE_DAILY_BACKUP" = "true" ]; then
    log_info "執行每日備份..."
    
    DAILY_BACKUP_DIR="$DAILY_DIR/$DATE_ONLY"
    mkdir -p "$DAILY_BACKUP_DIR"
    
    # 如果指定了資料庫列表，則備份指定的資料庫
    if [ -n "$BACKUP_DATABASES" ]; then
        IFS=',' read -ra DBS <<< "$BACKUP_DATABASES"
        
        for db in "${DBS[@]}"; do
            db=$(echo "$db" | xargs)  # 移除空白
            
            if [ "$BACKUP_FORMAT" = "custom" ]; then
                # 自訂格式（可用於平行還原）
                BACKUP_FILE="$DAILY_BACKUP_DIR/${db}_${TIMESTAMP}.dump"
                log_info "備份資料庫: $db (自訂格式)"
                
                if pg_dump -Fc -d "$db" -f "$BACKUP_FILE" 2>> "$LOG_FILE"; then
                    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
                    log_info "✓ 資料庫 $db 備份完成: $BACKUP_SIZE"
                else
                    log_error "✗ 資料庫 $db 備份失敗"
                fi
            else
                # SQL 格式
                BACKUP_FILE="$DAILY_BACKUP_DIR/${db}_${TIMESTAMP}.sql"
                log_info "備份資料庫: $db (SQL 格式)"
                
                if pg_dump -d "$db" --clean --if-exists > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
                    # 壓縮並加密備份檔案
                    BACKUP_FILE=$(compress_and_encrypt "$BACKUP_FILE")
                    if [ $? -eq 0 ]; then
                        BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
                        log_info "✓ 資料庫 $db 備份完成: $BACKUP_SIZE"
                    else
                        log_error "✗ 資料庫 $db 壓縮或加密失敗"
                    fi
                else
                    log_error "✗ 資料庫 $db 備份失敗"
                fi
            fi
        done
    else
        # 備份所有資料庫（排除系統資料庫）
        DATABASES=$(psql -d postgres -t -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres');" | xargs)
        
        for db in $DATABASES; do
            if [ "$BACKUP_FORMAT" = "custom" ]; then
                BACKUP_FILE="$DAILY_BACKUP_DIR/${db}_${TIMESTAMP}.dump"
                log_info "備份資料庫: $db (自訂格式)"
                
                if pg_dump -Fc -d "$db" -f "$BACKUP_FILE" 2>> "$LOG_FILE"; then
                    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
                    log_info "✓ 資料庫 $db 備份完成: $BACKUP_SIZE"
                else
                    log_error "✗ 資料庫 $db 備份失敗"
                fi
            else
                BACKUP_FILE="$DAILY_BACKUP_DIR/${db}_${TIMESTAMP}.sql"
                log_info "備份資料庫: $db (SQL 格式)"
                
                if pg_dump -d "$db" --clean --if-exists > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
                    # 壓縮並加密備份檔案
                    BACKUP_FILE=$(compress_and_encrypt "$BACKUP_FILE")
                    if [ $? -eq 0 ]; then
                        BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
                        log_info "✓ 資料庫 $db 備份完成: $BACKUP_SIZE"
                    else
                        log_error "✗ 資料庫 $db 壓縮或加密失敗"
                    fi
                else
                    log_error "✗ 資料庫 $db 備份失敗"
                fi
            fi
        done
    fi
fi

# ============================================================
# 3. 月異地備份（每月）
# ============================================================
if [ "$ENABLE_OFFSITE" = "true" ] && [ "$DAY_OF_MONTH" -eq "$OFFSITE_BACKUP_DAY" ]; then
    log_info "執行每月異地備份..."
    
    # 找到最新的週全量備份
    LATEST_FULL=$(find "$FULL_DIR" -mindepth 1 -maxdepth 1 -type d | sort -r | head -n1)
    
    if [ -n "$LATEST_FULL" ]; then
        MONTH_DIR=$(date '+%Y%m')
        OFFSITE_BACKUP_DIR="$OFFSITE_DIR/$MONTH_DIR"
        mkdir -p "$OFFSITE_BACKUP_DIR"
        
        log_info "複製最新完整備份到異地目錄: $LATEST_FULL"
        
        if cp -r "$LATEST_FULL"/* "$OFFSITE_BACKUP_DIR/" >> "$LOG_FILE" 2>&1; then
            log_info "異地備份（本地）完成: $OFFSITE_BACKUP_DIR"
            
            # 如果設定了遠端路徑，使用 rsync 推送
            if [ -n "$OFFSITE_REMOTE_PATH" ]; then
                log_info "推送到遠端: $OFFSITE_REMOTE_PATH"
                
                if rsync -avz --delete "$OFFSITE_BACKUP_DIR/" "$OFFSITE_REMOTE_PATH/$MONTH_DIR/" >> "$LOG_FILE" 2>&1; then
                    log_info "異地備份（遠端）完成"
                else
                    log_error "異地備份（遠端）失敗"
                fi
            fi
        else
            log_error "異地備份（本地）失敗"
        fi
    else
        log_error "找不到週全量備份，無法執行異地備份"
    fi
fi

# ============================================================
# 4. 自動刪除過期備份
# ============================================================
log_info "========== 開始清理過期備份 =========="

# 刪除過期的完整備份（保留最近 N 週）
if [ -d "$FULL_DIR" ]; then
    log_info "清理過期的完整備份（保留最近 $FULL_BACKUP_RETAIN_WEEKS 週）..."
    RETAIN_DAYS=$((FULL_BACKUP_RETAIN_WEEKS * 7))
    
    DELETED_COUNT=0
    while IFS= read -r dir; do
        if [ -n "$dir" ]; then
            rm -rf "$dir"
            ((DELETED_COUNT++))
        fi
    done < <(find "$FULL_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$RETAIN_DAYS 2>/dev/null)
    
    log_info "已刪除 $DELETED_COUNT 個過期的完整備份"
fi

# 刪除過期的每日備份（保留最近 N 天）
if [ -d "$DAILY_DIR" ]; then
    log_info "清理過期的每日備份（保留最近 $DAILY_RETAIN_DAYS 天）..."
    
    DELETED_COUNT=0
    while IFS= read -r dir; do
        if [ -n "$dir" ]; then
            rm -rf "$dir"
            ((DELETED_COUNT++))
        fi
    done < <(find "$DAILY_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$DAILY_RETAIN_DAYS 2>/dev/null)
    
    log_info "已刪除 $DELETED_COUNT 個過期的每日備份"
fi

# 刪除過期的異地備份（保留最近 N 個月）
if [ -d "$OFFSITE_DIR" ]; then
    log_info "清理過期的異地備份（保留最近 $OFFSITE_RETAIN_MONTHS 個月）..."
    RETAIN_DAYS=$((OFFSITE_RETAIN_MONTHS * 30))
    
    DELETED_COUNT=0
    while IFS= read -r dir; do
        if [ -n "$dir" ]; then
            rm -rf "$dir"
            ((DELETED_COUNT++))
        fi
    done < <(find "$OFFSITE_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$RETAIN_DAYS 2>/dev/null)
    
    log_info "已刪除 $DELETED_COUNT 個過期的異地備份"
fi

# 刪除過期的日誌檔案（保留最近 N 天）
if [ -f "$LOG_FILE" ]; then
    log_info "清理過期的日誌檔案（保留最近 $LOG_RETAIN_DAYS 天）..."
    find "$(dirname "$LOG_FILE")" -type f -name "*.log" -mtime +$LOG_RETAIN_DAYS -delete 2>> "$LOG_FILE"
fi

# ============================================================
# 5. 顯示備份統計資訊
# ============================================================
log_info "========== 備份統計 =========="

if [ -d "$FULL_DIR" ]; then
    FULL_COUNT=$(find "$FULL_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    FULL_SIZE=$(du -sh "$FULL_DIR" 2>/dev/null | cut -f1)
    log_info "完整備份：$FULL_COUNT 個，總大小：$FULL_SIZE"
fi

if [ -d "$DAILY_DIR" ]; then
    DAILY_COUNT=$(find "$DAILY_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    DAILY_SIZE=$(du -sh "$DAILY_DIR" 2>/dev/null | cut -f1)
    log_info "每日備份：$DAILY_COUNT 個，總大小：$DAILY_SIZE"
fi

if [ -d "$OFFSITE_DIR" ]; then
    OFFSITE_COUNT=$(find "$OFFSITE_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    OFFSITE_SIZE=$(du -sh "$OFFSITE_DIR" 2>/dev/null | cut -f1)
    log_info "異地備份：$OFFSITE_COUNT 個，總大小：$OFFSITE_SIZE"
fi

log_info "========== 備份完成 =========="

# 清除密碼環境變數
unset PGPASSWORD
