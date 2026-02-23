#!/bin/sh
# ============================================================================
# MinIO 備份腳本 (使用 mc - MinIO 官方客戶端工具)
#
# 這個腳本使用 MinIO 官方提供的 mc (MinIO Client) 工具進行物件儲存備份。
# mc 是專為 S3 相容儲存設計的命令列工具，被 GitLab、Kubernetes Velero 等
# 廣泛採用於自動化備份場景。
#
# 技術說明:
# - mc 自動處理大檔案分塊傳輸 (multipart upload)
# - 支援斷點續傳和錯誤自動重試
# - 相容任何 S3 相容儲存 (AWS S3, MinIO, GCS 等)
# - 保留檔案元資料 (metadata)
#
# 備份流程:
# 1. mc cp --recursive: 遞迴下載 Bucket 所有檔案
# 2. tar: 打包成單一歸檔
# 3. gzip: 壓縮減少備份大小 (可選)
# 4. openssl enc: AES 加密保護 (可選)
#
# 參考文獻:
# - MinIO Client: https://min.io/docs/minio/linux/reference/minio-mc.html
# - MinIO 備份指南: https://min.io/docs/minio/linux/operations/install-deploy-manage/migrate-fs-gateway.html
#
# 支援功能: Bucket 備份 / 壓縮 / 加密 / 自動清理
# ============================================================================

set -e

# 載入配置 (優先使用環境變數，其次使用配置檔)
CONFIG_FILE="${CONFIG_FILE:-/scripts/config/.env}"
if [ -f "$CONFIG_FILE" ]; then
    # 只載入配置檔中未被環境變數覆蓋的值
    while IFS='=' read -r key value; do
        # 跳過註解和空行
        case "$key" in
            '#'*|'') continue ;;
        esac
        # 只有當環境變數未設定時才使用配置檔的值
        eval "current_val=\${$key:-}"
        if [ -z "$current_val" ]; then
            export "$key=$value"
        fi
    done < "$CONFIG_FILE"
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
