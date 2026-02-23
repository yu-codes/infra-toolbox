#!/bin/bash

# ============================================================
# MinIO 還原腳本
# ============================================================
# 功能：
#   1. 從完整備份還原
#   2. 從增量備份還原
#   3. 從異地備份還原
#   4. 支援指定日期還原
#   5. 支援還原到不同的 MinIO 實例
# ============================================================

set -e

# 載入環境變數
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/backup.env"

# 載入加密工具函數
source "$SCRIPT_DIR/crypto_utils.sh"

# 載入還原設定（如果存在）
if [ -f "$SCRIPT_DIR/restore.env" ]; then
    source "$SCRIPT_DIR/restore.env"
fi

# 日誌函數
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# 檢查 mc 是否安裝
if ! command -v mc &> /dev/null; then
    log_error "mc (MinIO Client) 未安裝，請先安裝：https://min.io/docs/minio/linux/reference/minio-mc.html"
    exit 1
fi

# 顯示使用說明
show_usage() {
    cat << EOF
使用方式：
    $0 [選項]

選項：
    -t, --type <TYPE>           備份類型 (full/incremental/offsite)
    -d, --date <DATE>           備份日期 (格式：YYYYMMDD 或 YYYYMM)
    -b, --bucket <BUCKET>       指定要還原的 bucket（不指定則還原全部）
    -r, --target <ALIAS>        還原目標 MinIO alias（預設：dbminio）
    -l, --list                  列出可用的備份
    -n, --dry-run               預覽模式（不實際執行）
    -f, --force                 強制覆蓋，不詢問確認
    -h, --help                  顯示此說明

範例：
    # 列出所有可用的完整備份
    $0 --list --type full

    # 從 2026-02-23 的完整備份還原
    $0 --type full --date 20260223

    # 從增量備份還原特定 bucket
    $0 --type incremental --date 20260223 --bucket my-bucket

    # 預覽還原操作
    $0 --type full --date 20260223 --dry-run

    # 還原到不同的 MinIO 實例
    $0 --type full --date 20260223 --target new_minio

EOF
}

# 列出可用的備份
list_backups() {
    local backup_type=$1
    local backup_dir=""

    case $backup_type in
        full)
            backup_dir="$FULL_DIR"
            ;;
        incremental)
            backup_dir="$INCREMENTAL_DIR"
            ;;
        offsite)
            backup_dir="$OFFSITE_DIR"
            ;;
        *)
            log_error "無效的備份類型：$backup_type"
            exit 1
            ;;
    esac

    if [ ! -d "$backup_dir" ]; then
        log_error "備份目錄不存在：$backup_dir"
        exit 1
    fi

    echo "=========================================="
    echo "可用的 ${backup_type} 備份："
    echo "=========================================="

    local backups=$(find "$backup_dir" -maxdepth 1 -type d -name "20*" | sort -r)
    
    if [ -z "$backups" ]; then
        echo "無可用備份"
        return
    fi

    for backup in $backups; do
        local date=$(basename "$backup")
        local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
        local files=$(find "$backup" -type f 2>/dev/null | wc -l)
        echo "  [$date]  大小: $size  檔案數: $files"
    done

    echo "=========================================="
}

# 驗證備份是否存在
validate_backup() {
    local backup_type=$1
    local backup_date=$2
    local backup_dir=""

    case $backup_type in
        full)
            backup_dir="$FULL_DIR/$backup_date"
            ;;
        incremental)
            backup_dir="$INCREMENTAL_DIR/$backup_date"
            ;;
        offsite)
            backup_dir="$OFFSITE_DIR/$backup_date"
            ;;
    esac

    if [ ! -d "$backup_dir" ]; then
        log_error "備份不存在：$backup_dir"
        return 1
    fi

    echo "$backup_dir"
    return 0
}

# 執行還原
perform_restore() {
    local backup_type=$1
    local backup_date=$2
    local target_bucket=$3
    local target_alias=$4
    local dry_run=$5
    local force=$6

    # 驗證備份
    local backup_path=$(validate_backup "$backup_type" "$backup_date")
    if [ $? -ne 0 ]; then
        exit 1
    fi
    
    # 處理加密和壓縮的備份檔案
    local original_backup_path="$backup_path"
    local temp_extract_dir=""
    
    # 檢查是否有加密的 tar 備份檔案
    local backup_file=$(find "$backup_path" -type f -name "*.tar*" 2>/dev/null | head -n1)
    
    if [ -n "$backup_file" ]; then
        log_info "檢測到打包備份檔案: $(basename "$backup_file")"
        
        # 解密和解壓縮
        local processed_file="$backup_file"
        local temp_file=""
        
        if [[ "$backup_file" == *.enc* ]]; then
            log_info "開始解密和解壓縮備份檔案..."
            temp_file=$(decrypt_and_decompress "$backup_file")
            if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                log_error "解密或解壓縮失敗"
                exit 1
            fi
            processed_file="$temp_file"
            log_info "解密和解壓縮完成"
        elif [[ "$backup_file" =~ \.(gz|bz2|xz)$ ]]; then
            log_info "開始解壓縮備份檔案..."
            temp_file=$(decompress_file "$backup_file")
            if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                log_error "解壓縮失敗"
                exit 1
            fi
            processed_file="$temp_file"
            log_info "解壓縮完成"
        fi
        
        # 解包 tar 檔案
        temp_extract_dir="$(mktemp -d)"
        log_info "解包備份檔案到: $temp_extract_dir"
        
        if tar -xf "$processed_file" -C "$temp_extract_dir" >> "$LOG_FILE" 2>&1; then
            log_info "解包完成"
            
            # 清理臨時壓縮檔案
            if [ -n "$temp_file" ]; then
                rm -f "$temp_file"
            fi
            
            # 更新 backup_path 為解包後的目錄
            backup_path="$temp_extract_dir/data"
        else
            log_error "解包失敗"
            
            # 清理臨時檔案
            if [ -n "$temp_file" ]; then
                rm -f "$temp_file"
            fi
            rm -rf "$temp_extract_dir"
            exit 1
        fi
    fi

    log_info "========== 開始還原 =========="
    log_info "備份類型：$backup_type"
    log_info "備份日期：$backup_date"
    log_info "備份路徑：$backup_path"
    log_info "還原目標：$target_alias"

    # 設定 mc alias
    mc alias set dbminio "$MINIO_HOST" "$MINIO_USER" "$MINIO_PASS" > /dev/null 2>&1 || {
        log_error "無法連線至 MinIO: $MINIO_HOST"
        exit 1
    }

    # 檢查目標 alias 是否存在
    if ! mc alias list | grep -q "^$target_alias"; then
        log_error "目標 alias 不存在：$target_alias"
        log_info "可用的 alias："
        mc alias list
        exit 1
    fi

    # 確認操作
    if [ "$force" != "true" ] && [ "$dry_run" != "true" ]; then
        echo ""
        echo "=========================================="
        echo "⚠️  警告：此操作將會覆蓋目標 MinIO 的資料！"
        echo "=========================================="
        echo "備份來源：$backup_path"
        echo "還原目標：$target_alias"
        if [ -n "$target_bucket" ]; then
            echo "還原 Bucket：$target_bucket"
        else
            echo "還原範圍：全部 buckets"
        fi
        echo "=========================================="
        read -p "確定要繼續嗎？(yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            log_info "使用者取消還原操作"
            exit 0
        fi
    fi

    # 執行還原
    if [ -n "$target_bucket" ]; then
        # 還原特定 bucket
        local source_path="$backup_path/$target_bucket"
        
        if [ ! -d "$source_path" ]; then
            log_error "備份中不存在 bucket：$target_bucket"
            # 清理臨時解包目錄
            if [ -n "$temp_extract_dir" ] && [ -d "$temp_extract_dir" ]; then
                rm -rf "$temp_extract_dir"
            fi
            exit 1
        fi

        if [ "$dry_run" = "true" ]; then
            log_info "[預覽模式] 將執行："
            echo "mc mirror --overwrite $source_path $target_alias/$target_bucket"
        else
            log_info "還原 bucket：$target_bucket"
            if mc mirror --overwrite "$source_path" "$target_alias/$target_bucket" >> "$LOG_FILE" 2>&1; then
                log_info "✓ Bucket $target_bucket 還原完成"
            else
                log_error "✗ Bucket $target_bucket 還原失敗"
                # 清理臨時解包目錄
                if [ -n "$temp_extract_dir" ] && [ -d "$temp_extract_dir" ]; then
                    rm -rf "$temp_extract_dir"
                fi
                exit 1
            fi
        fi
    else
        # 還原所有 buckets
        local buckets=$(find "$backup_path" -maxdepth 1 -type d ! -path "$backup_path" -exec basename {} \;)
        
        if [ -z "$buckets" ]; then
            log_error "備份中沒有找到任何 bucket"
            # 清理臨時解包目錄
            if [ -n "$temp_extract_dir" ] && [ -d "$temp_extract_dir" ]; then
                rm -rf "$temp_extract_dir"
            fi
            exit 1
        fi

        if [ "$dry_run" = "true" ]; then
            log_info "[預覽模式] 將還原以下 buckets："
            for bucket in $buckets; do
                echo "  - $bucket"
                echo "    mc mirror --overwrite $backup_path/$bucket $target_alias/$bucket"
            done
        else
            local success_count=0
            local fail_count=0

            for bucket in $buckets; do
                log_info "還原 bucket：$bucket"
                
                if mc mirror --overwrite "$backup_path/$bucket" "$target_alias/$bucket" >> "$LOG_FILE" 2>&1; then
                    log_info "✓ Bucket $bucket 還原完成"
                    ((success_count++))
                else
                    log_error "✗ Bucket $bucket 還原失敗"
                    ((fail_count++))
                fi
            done

            log_info "========== 還原完成 =========="
            log_info "成功：$success_count 個 buckets"
            log_info "失敗：$fail_count 個 buckets"
        fi
    fi

    if [ "$dry_run" != "true" ]; then
        log_info "========== 還原操作完成 =========="
    fi
    
    # 清理臨時解包目錄
    if [ -n "$temp_extract_dir" ] && [ -d "$temp_extract_dir" ]; then
        log_info "清理臨時檔案..."
        rm -rf "$temp_extract_dir"
    fi
}

# 主程式
main() {
    local backup_type=""
    local backup_date=""
    local target_bucket=""
    local target_alias="dbminio"
    local list_mode=false
    local dry_run=false
    local force=false

    # 解析參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                backup_type="$2"
                shift 2
                ;;
            -d|--date)
                backup_date="$2"
                shift 2
                ;;
            -b|--bucket)
                target_bucket="$2"
                shift 2
                ;;
            -r|--target)
                target_alias="$2"
                shift 2
                ;;
            -l|--list)
                list_mode=true
                shift
                ;;
            -n|--dry-run)
                dry_run=true
                shift
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知的選項：$1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 列出備份模式
    if [ "$list_mode" = true ]; then
        if [ -z "$backup_type" ]; then
            list_backups "full"
            echo ""
            list_backups "incremental"
            echo ""
            list_backups "offsite"
        else
            list_backups "$backup_type"
        fi
        exit 0
    fi

    # 驗證必要參數
    if [ -z "$backup_type" ] || [ -z "$backup_date" ]; then
        log_error "必須指定備份類型 (-t) 和備份日期 (-d)"
        echo ""
        show_usage
        exit 1
    fi

    # 驗證備份類型
    if [[ ! "$backup_type" =~ ^(full|incremental|offsite)$ ]]; then
        log_error "無效的備份類型：$backup_type（必須是 full、incremental 或 offsite）"
        exit 1
    fi

    # 執行還原
    perform_restore "$backup_type" "$backup_date" "$target_bucket" "$target_alias" "$dry_run" "$force"
}

# 執行主程式
main "$@"
