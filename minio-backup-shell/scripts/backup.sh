#!/bin/bash

# ============================================================
# MinIO 自動化備份腳本（含自動刪舊機制）
# ============================================================
# 功能：
#   1. 週全量備份
#   2. 日增量備份
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

# 檢查 mc 是否安裝
if ! command -v mc &> /dev/null; then
    log_error "mc (MinIO Client) 未安裝，請先安裝：https://min.io/docs/minio/linux/reference/minio-mc.html"
    exit 1
fi

# 檢查加密與壓縮工具
if ! check_crypto_tools "$ENCRYPTION_METHOD" "$COMPRESSION_TYPE"; then
    log_error "加密或壓縮工具未安裝"
    exit 1
fi

# 建立必要目錄
mkdir -p "$FULL_DIR" "$INCREMENTAL_DIR" "$OFFSITE_DIR" "$(dirname "$LOG_FILE")"

# 設定 mc alias
log_info "設定 MinIO alias..."
mc alias set dbminio "$MINIO_HOST" "$MINIO_USER" "$MINIO_PASS" > /dev/null 2>&1 || {
    log_error "無法連線至 MinIO: $MINIO_HOST"
    exit 1
}

DAY_OF_WEEK=$(date +%w)
DAY_OF_MONTH=$(date +%d)

log_info "========== 開始執行備份 =========="

# ============================================================
# 1. 週全量備份（每週一次）
# ============================================================
if [ "$ENABLE_FULL_BACKUP" = "true" ] && [ "$DAY_OF_WEEK" -eq "$FULL_BACKUP_DAY" ]; then
    log_info "執行每週完整備份..."
    
    FULL_BACKUP_DIR="$FULL_DIR/$(date '+%Y%m%d')"
    FULL_BACKUP_TEMP="$FULL_BACKUP_DIR/data"
    mkdir -p "$FULL_BACKUP_TEMP"
    
    if mc mirror --overwrite --remove dbminio "$FULL_BACKUP_TEMP" >> "$LOG_FILE" 2>&1; then
        log_info "週全量備份同步完成"
        
        # 打包、壓縮並加密
        ARCHIVE_FILE="$FULL_BACKUP_DIR/full_backup_$(date '+%Y%m%d_%H%M%S').tar"
        log_info "打包備份檔案..."
        
        if tar -cf "$ARCHIVE_FILE" -C "$FULL_BACKUP_DIR" data >> "$LOG_FILE" 2>&1; then
            # 刪除臨時目錄
            rm -rf "$FULL_BACKUP_TEMP"
            
            # 壓縮並加密
            FINAL_FILE=$(compress_and_encrypt "$ARCHIVE_FILE")
            if [ $? -eq 0 ]; then
                BACKUP_SIZE=$(du -sh "$FINAL_FILE" | cut -f1)
                log_info "週全量備份完成: $FINAL_FILE (大小: $BACKUP_SIZE)"
            else
                log_error "壓縮或加密失敗"
            fi
        else
            log_error "打包失敗"
            rm -rf "$FULL_BACKUP_TEMP"
        fi
    else
        log_error "週全量備份失敗"
    fi
fi

# ============================================================
# 2. 日增量備份（每日）
# ============================================================
if [ "$ENABLE_INCREMENTAL" = "true" ]; then
    log_info "執行每日增量備份..."
    
    INCREMENTAL_BACKUP_DIR="$INCREMENTAL_DIR/$(date '+%Y%m%d')"
    INCREMENTAL_BACKUP_TEMP="$INCREMENTAL_BACKUP_DIR/data"
    mkdir -p "$INCREMENTAL_BACKUP_TEMP"
    
    if mc mirror --overwrite --remove dbminio "$INCREMENTAL_BACKUP_TEMP" >> "$LOG_FILE" 2>&1; then
        log_info "日增量備份同步完成"
        
        # 打包、壓縮並加密
        ARCHIVE_FILE="$INCREMENTAL_BACKUP_DIR/incremental_backup_$(date '+%Y%m%d_%H%M%S').tar"
        log_info "打包備份檔案..."
        
        if tar -cf "$ARCHIVE_FILE" -C "$INCREMENTAL_BACKUP_DIR" data >> "$LOG_FILE" 2>&1; then
            # 刪除臨時目錄
            rm -rf "$INCREMENTAL_BACKUP_TEMP"
            
            # 壓縮並加密
            FINAL_FILE=$(compress_and_encrypt "$ARCHIVE_FILE")
            if [ $? -eq 0 ]; then
                BACKUP_SIZE=$(du -sh "$FINAL_FILE" | cut -f1)
                log_info "日增量備份完成: $FINAL_FILE (大小: $BACKUP_SIZE)"
            else
                log_error "壓縮或加密失敗"
            fi
        else
            log_error "打包失敗"
            rm -rf "$INCREMENTAL_BACKUP_TEMP"
        fi
    else
        log_error "日增量備份失敗"
    fi
fi

# ============================================================
# 3. 月異地備份（每月）
# ============================================================
if [ "$ENABLE_OFFSITE" = "true" ] && [ "$DAY_OF_MONTH" -eq "$OFFSITE_BACKUP_DAY" ]; then
    log_info "執行每月異地備份..."
    
    # 找到最新的週全量備份檔案
    LATEST_FULL=$(find "$FULL_DIR" -type f -name "full_backup_*" 2>/dev/null | sort -r | head -n1)
    
    if [ -n "$LATEST_FULL" ]; then
        OFFSITE_BACKUP_DIR="$OFFSITE_DIR/$(date '+%Y%m')"
        mkdir -p "$OFFSITE_BACKUP_DIR"
        
        OFFSITE_FILE="$OFFSITE_BACKUP_DIR/$(basename "$LATEST_FULL")"
        
        # 先複製到本地異地目錄
        if cp "$LATEST_FULL" "$OFFSITE_FILE" >> "$LOG_FILE" 2>&1; then
            BACKUP_SIZE=$(du -sh "$OFFSITE_FILE" | cut -f1)
            log_info "異地備份（本地）完成: $OFFSITE_FILE (大小: $BACKUP_SIZE)"
            
            # 如果有設定遠端 alias，推送到遠端
            if mc alias list | grep -q "$OFFSITE_ALIAS"; then
                if mc cp "$OFFSITE_FILE" "$OFFSITE_ALIAS/minio-backup/$(date '+%Y%m')/$(basename "$OFFSITE_FILE")" >> "$LOG_FILE" 2>&1; then
                    log_info "異地備份（遠端）完成: $OFFSITE_ALIAS"
                else
                    log_error "異地備份（遠端）失敗"
                fi
            fi
        else
            log_error "異地備份（本地）失敗"
        fi
    else
        log_error "找不到週全量備份檔案，無法執行異地備份"
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
    find "$FULL_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETAIN_DAYS -exec rm -rf {} \; 2>> "$LOG_FILE"
    DELETED_COUNT=$(find "$FULL_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETAIN_DAYS 2>/dev/null | wc -l)
    log_info "已刪除 $DELETED_COUNT 個過期的完整備份"
fi

# 刪除過期的增量備份（保留最近 N 天）
if [ -d "$INCREMENTAL_DIR" ]; then
    log_info "清理過期的增量備份（保留最近 $INCREMENTAL_RETAIN_DAYS 天）..."
    find "$INCREMENTAL_DIR" -maxdepth 1 -type d -name "20*" -mtime +$INCREMENTAL_RETAIN_DAYS -exec rm -rf {} \; 2>> "$LOG_FILE"
    DELETED_COUNT=$(find "$INCREMENTAL_DIR" -maxdepth 1 -type d -name "20*" -mtime +$INCREMENTAL_RETAIN_DAYS 2>/dev/null | wc -l)
    log_info "已刪除 $DELETED_COUNT 個過期的增量備份"
fi

# 刪除過期的異地備份（保留最近 N 個月）
if [ -d "$OFFSITE_DIR" ]; then
    log_info "清理過期的異地備份（保留最近 $OFFSITE_RETAIN_MONTHS 個月）..."
    RETAIN_DAYS=$((OFFSITE_RETAIN_MONTHS * 30))
    find "$OFFSITE_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETAIN_DAYS -exec rm -rf {} \; 2>> "$LOG_FILE"
    DELETED_COUNT=$(find "$OFFSITE_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETAIN_DAYS 2>/dev/null | wc -l)
    log_info "已刪除 $DELETED_COUNT 個過期的異地備份"
fi

# 刪除過期的日誌檔案（保留最近 N 天）
if [ -f "$LOG_FILE" ]; then
    log_info "清理過期的日誌檔案（保留最近 $LOG_RETAIN_DAYS 天）..."
    find "$(dirname "$LOG_FILE")" -type f -name "*.log" -mtime +$LOG_RETAIN_DAYS -exec rm -f {} \; 2>> "$LOG_FILE"
fi

# ============================================================
# 5. 顯示備份統計資訊
# ============================================================
log_info "========== 備份統計 =========="

if [ -d "$FULL_DIR" ]; then
    FULL_COUNT=$(find "$FULL_DIR" -maxdepth 1 -type d -name "20*" 2>/dev/null | wc -l)
    FULL_SIZE=$(du -sh "$FULL_DIR" 2>/dev/null | cut -f1)
    log_info "完整備份：$FULL_COUNT 個，總大小：$FULL_SIZE"
fi

if [ -d "$INCREMENTAL_DIR" ]; then
    INCREMENTAL_COUNT=$(find "$INCREMENTAL_DIR" -maxdepth 1 -type d -name "20*" 2>/dev/null | wc -l)
    INCREMENTAL_SIZE=$(du -sh "$INCREMENTAL_DIR" 2>/dev/null | cut -f1)
    log_info "增量備份：$INCREMENTAL_COUNT 個，總大小：$INCREMENTAL_SIZE"
fi

if [ -d "$OFFSITE_DIR" ]; then
    OFFSITE_COUNT=$(find "$OFFSITE_DIR" -maxdepth 1 -type d -name "20*" 2>/dev/null | wc -l)
    OFFSITE_SIZE=$(du -sh "$OFFSITE_DIR" 2>/dev/null | cut -f1)
    log_info "異地備份：$OFFSITE_COUNT 個，總大小：$OFFSITE_SIZE"
fi

log_info "========== 備份完成 =========="
