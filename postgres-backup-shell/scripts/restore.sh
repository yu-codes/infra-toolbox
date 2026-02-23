#!/bin/bash

# ============================================================
# PostgreSQL 還原腳本
# ============================================================
# 功能：
#   1. 從完整備份還原（pg_dumpall 格式）
#   2. 從每日備份還原（pg_dump 格式）
#   3. 從異地備份還原
#   4. 支援指定日期還原
#   5. 支援還原特定資料庫或全部
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

# 檢查工具是否安裝
check_tools() {
    if ! command -v psql &> /dev/null; then
        log_error "psql 未安裝，請先安裝 PostgreSQL 客戶端工具"
        exit 1
    fi
    
    if ! command -v pg_restore &> /dev/null; then
        log_error "pg_restore 未安裝，請先安裝 PostgreSQL 客戶端工具"
        exit 1
    fi
}

# 顯示使用說明
show_usage() {
    cat << EOF
使用方式：
    $0 [選項]

選項：
    -t, --type <TYPE>           備份類型 (full/daily/offsite)
    -d, --date <DATE>           備份日期 (格式：YYYYMMDD 或 YYYYMM)
    -D, --database <DB>         指定要還原的資料庫（僅適用於 daily 類型）
    -f, --file <FILE>           直接指定備份檔案路徑
    -H, --host <HOST>           目標資料庫主機（預設：使用 backup.env 設定）
    -p, --port <PORT>           目標資料庫埠號（預設：使用 backup.env 設定）
    -U, --user <USER>           目標資料庫使用者（預設：使用 backup.env 設定）
    -l, --list                  列出可用的備份
    -n, --dry-run               預覽模式（不實際執行）
    --force                     強制覆蓋，不詢問確認
    --drop-database             還原前先刪除資料庫（謹慎使用）
    -h, --help                  顯示此說明

範例：
    # 列出所有可用的完整備份
    $0 --list --type full

    # 從完整備份還原所有資料庫
    $0 --type full --date 20260223

    # 從每日備份還原特定資料庫
    $0 --type daily --date 20260223 --database mydb

    # 直接指定備份檔案還原
    $0 --file /opt/pg-backup/daily/20260223/mydb_20260223_020000.sql.gz

    # 預覽還原操作
    $0 --type full --date 20260223 --dry-run

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
        daily)
            backup_dir="$DAILY_DIR"
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

    local backups=$(find "$backup_dir" -mindepth 1 -maxdepth 1 -type d | sort -r)
    
    if [ -z "$backups" ]; then
        echo "無可用備份"
        return
    fi

    for backup in $backups; do
        local date=$(basename "$backup")
        local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
        local files=$(find "$backup" -type f 2>/dev/null | wc -l)
        echo "  [$date]  大小: $size  檔案數: $files"
        
        # 顯示檔案列表
        if [ "$backup_type" = "daily" ]; then
            echo "          檔案："
            find "$backup" -type f -name "*.sql*" -o -name "*.dump" | while read -r file; do
                local fname=$(basename "$file")
                local fsize=$(du -sh "$file" | cut -f1)
                echo "            - $fname ($fsize)"
            done
        fi
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
        daily)
            backup_dir="$DAILY_DIR/$backup_date"
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

# 還原完整備份（pg_dumpall 格式）
restore_full_backup() {
    local backup_path=$1
    local dry_run=$2
    local target_host=${3:-$PG_HOST}
    local target_port=${4:-$PG_PORT}
    local target_user=${5:-$PG_USER}
    
    # 找到備份檔案
    local backup_file=$(find "$backup_path" -name "full_backup_*.sql*" | head -n1)
    
    if [ -z "$backup_file" ]; then
        log_error "在 $backup_path 中找不到完整備份檔案"
        return 1
    fi
    
    log_info "找到備份檔案: $(basename "$backup_file")"
    
    if [ "$dry_run" = "true" ]; then
        log_info "[預覽模式] 將執行："
        if [[ "$backup_file" == *.gz ]]; then
            echo "gunzip -c $backup_file | psql -h $target_host -p $target_port -U $target_user -d postgres"
        else
            echo "psql -h $target_host -p $target_port -U $target_user -d postgres -f $backup_file"
        fi
        return 0
    fi
    
    log_info "開始還原完整備份..."
    
    export PGHOST="$target_host"
    export PGPORT="$target_port"
    export PGUSER="$target_user"
    export PGPASSWORD="$PG_PASSWORD"
    
    # 處理加密和壓縮的備份檔案
    local processed_file="$backup_file"
    local temp_file=""
    
    # 如果檔案是加密的，先解密和解壓縮
    if [[ "$backup_file" == *.enc* ]]; then
        log_info "檢測到加密備份，開始解密和解壓縮..."
        temp_file=$(decrypt_and_decompress "$backup_file")
        if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
            log_error "解密或解壓縮失敗"
            return 1
        fi
        processed_file="$temp_file"
        log_info "解密和解壓縮完成: $processed_file"
    elif [[ "$backup_file" == *.gz ]] || [[ "$backup_file" == *.bz2 ]] || [[ "$backup_file" == *.xz ]]; then
        log_info "檢測到壓縮備份，開始解壓縮..."
        temp_file=$(decompress_file "$backup_file")
        if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
            log_error "解壓縮失敗"
            return 1
        fi
        processed_file="$temp_file"
        log_info "解壓縮完成: $processed_file"
    fi
    
    # 執行還原
    if psql -d postgres -f "$processed_file" >> "$LOG_FILE" 2>&1; then
        log_info "✓ 完整備份還原成功"
        
        # 清理臨時檔案
        if [ -n "$temp_file" ]; then
            rm -f "$temp_file"
        fi
        return 0
    else
        log_error "✗ 完整備份還原失敗"
        
        # 清理臨時檔案
        if [ -n "$temp_file" ]; then
            rm -f "$temp_file"
        fi
        return 1
    fi
        if psql -d postgres -f "$backup_file" >> "$LOG_FILE" 2>&1; then
            log_info "✓ 完整備份還原成功"
            return 0
        else
            log_error "✗ 完整備份還原失敗"
            return 1
        fi
    fi
}

# 還原每日備份（pg_dump 格式）
restore_daily_backup() {
    local backup_path=$1
    local database=$2
    local dry_run=$3
    local drop_db=$4
    local target_host=${5:-$PG_HOST}
    local target_port=${6:-$PG_PORT}
    local target_user=${7:-$PG_USER}
    
    export PGHOST="$target_host"
    export PGPORT="$target_port"
    export PGUSER="$target_user"
    export PGPASSWORD="$PG_PASSWORD"
    
    if [ -n "$database" ]; then
        # 還原特定資料庫
        local backup_file=$(find "$backup_path" -name "${database}_*.sql*" -o -name "${database}_*.dump" | head -n1)
        
        if [ -z "$backup_file" ]; then
            log_error "找不到資料庫 $database 的備份檔案"
            return 1
        fi
        
        log_info "找到備份檔案: $(basename "$backup_file")"
        
        if [ "$dry_run" = "true" ]; then
            log_info "[預覽模式] 將還原資料庫: $database"
            echo "備份檔案: $backup_file"
            return 0
        fi
        
        # 檢查資料庫是否存在
        DB_EXISTS=$(psql -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$database';" | xargs)
        
        if [ "$drop_db" = "true" ] && [ "$DB_EXISTS" = "1" ]; then
            log_warning "刪除現有資料庫: $database"
            psql -d postgres -c "DROP DATABASE IF EXISTS \"$database\";" >> "$LOG_FILE" 2>&1
        fi
        
        # 如果資料庫不存在，創建它
        if [ "$DB_EXISTS" != "1" ] || [ "$drop_db" = "true" ]; then
            log_info "創建資料庫: $database"
            psql -d postgres -c "CREATE DATABASE \"$database\";" >> "$LOG_FILE" 2>&1
        fi
        
        log_info "還原資料庫: $database"
        
        # 處理加密和壓縮的備份檔案
        local processed_file="$backup_file"
        local temp_file=""
        local is_dump_format=false
        
        # 判斷是否為 dump 格式（從原始檔名判斷）
        if [[ "$backup_file" =~ \.dump(\.gz|\.bz2|\.xz)?(\.enc)?$ ]]; then
            is_dump_format=true
        fi
        
        # 如果檔案是加密的，先解密和解壓縮
        if [[ "$backup_file" == *.enc* ]]; then
            log_info "檢測到加密備份，開始解密和解壓縮..."
            temp_file=$(decrypt_and_decompress "$backup_file")
            if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                log_error "解密或解壓縮失敗"
                return 1
            fi
            processed_file="$temp_file"
            log_info "解密和解壓縮完成: $processed_file"
        elif [[ "$backup_file" =~ \.(gz|bz2|xz)$ ]]; then
            log_info "檢測到壓縮備份，開始解壓縮..."
            temp_file=$(decompress_file "$backup_file")
            if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                log_error "解壓縮失敗"
                return 1
            fi
            processed_file="$temp_file"
            log_info "解壓縮完成: $processed_file"
        fi
        
        # 根據格式還原
        local restore_success=false
        if [ "$is_dump_format" = true ] || [[ "$processed_file" == *.dump ]]; then
            # 自訂格式
            if pg_restore -d "$database" --clean --if-exists "$processed_file" >> "$LOG_FILE" 2>&1; then
                log_info "✓ 資料庫 $database 還原成功"
                restore_success=true
            else
                log_error "✗ 資料庫 $database 還原失敗"
            fi
        else
            # SQL 檔案
            if psql -d "$database" -f "$processed_file" >> "$LOG_FILE" 2>&1; then
                log_info "✓ 資料庫 $database 還原成功"
                restore_success=true
            else
                log_error "✗ 資料庫 $database 還原失敗"
            fi
        fi
        
        # 清理臨時檔案
        if [ -n "$temp_file" ]; then
            rm -f "$temp_file"
        fi
        
        if [ "$restore_success" = true ]; then
            return 0
        else
            return 1
        fi
    else
        # 還原所有資料庫
        local backup_files=$(find "$backup_path" -name "*.sql*" -o -name "*.dump")
        
        if [ -z "$backup_files" ]; then
            log_error "在 $backup_path 中找不到備份檔案"
            return 1
        fi
        
        if [ "$dry_run" = "true" ]; then
            log_info "[預覽模式] 將還原以下資料庫："
            echo "$backup_files" | while read -r file; do
                echo "  - $(basename "$file")"
            done
            return 0
        fi
        
        local success_count=0
        local fail_count=0
        
        echo "$backup_files" | while read -r backup_file; do
            # 從檔案名稱提取資料庫名稱
            local filename=$(basename "$backup_file")
            local dbname=$(echo "$filename" | sed 's/_[0-9]\{8\}_[0-9]\{6\}.*//')
            
            log_info "還原資料庫: $dbname"
            
            # 檢查資料庫是否存在
            DB_EXISTS=$(psql -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$dbname';" | xargs)
            
            if [ "$drop_db" = "true" ] && [ "$DB_EXISTS" = "1" ]; then
                psql -d postgres -c "DROP DATABASE IF EXISTS \"$dbname\";" >> "$LOG_FILE" 2>&1
            fi
            
            if [ "$DB_EXISTS" != "1" ] || [ "$drop_db" = "true" ]; then
                psql -d postgres -c "CREATE DATABASE \"$dbname\";" >> "$LOG_FILE" 2>&1
            fi
            
            # 處理加密和壓縮的備份檔案
            local processed_file="$backup_file"
            local temp_file=""
            local is_dump_format=false
            
            # 判斷是否為 dump 格式（從原始檔名判斷）
            if [[ "$backup_file" =~ \.dump(\.gz|\.bz2|\.xz)?(\.enc)?$ ]]; then
                is_dump_format=true
            fi
            
            # 如果檔案是加密的，先解密和解壓縮
            if [[ "$backup_file" == *.enc* ]]; then
                temp_file=$(decrypt_and_decompress "$backup_file")
                if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                    log_error "解密或解壓縮失敗: $backup_file"
                    ((fail_count++))
                    continue
                fi
                processed_file="$temp_file"
            elif [[ "$backup_file" =~ \.(gz|bz2|xz)$ ]]; then
                temp_file=$(decompress_file "$backup_file")
                if [ $? -ne 0 ] || [ -z "$temp_file" ]; then
                    log_error "解壓縮失敗: $backup_file"
                    ((fail_count++))
                    continue
                fi
                processed_file="$temp_file"
            fi
            
            # 根據格式還原
            if [ "$is_dump_format" = true ] || [[ "$processed_file" == *.dump ]]; then
                if pg_restore -d "$dbname" --clean --if-exists "$processed_file" >> "$LOG_FILE" 2>&1; then
                    log_info "✓ 資料庫 $dbname 還原成功"
                    ((success_count++))
                else
                    log_error "✗ 資料庫 $dbname 還原失敗"
                    ((fail_count++))
                fi
            else
                if psql -d "$dbname" -f "$processed_file" >> "$LOG_FILE" 2>&1; then
                    log_info "✓ 資料庫 $dbname 還原成功"
                    ((success_count++))
                else
                    log_error "✗ 資料庫 $dbname 還原失敗"
                    ((fail_count++))
                fi
            fi
            
            # 清理臨時檔案
            if [ -n "$temp_file" ]; then
                rm -f "$temp_file"
            fi
        done
        
        log_info "還原完成 - 成功: $success_count, 失敗: $fail_count"
    fi
}

# 主程式
main() {
    local backup_type=""
    local backup_date=""
    local database=""
    local backup_file=""
    local target_host="$PG_HOST"
    local target_port="$PG_PORT"
    local target_user="$PG_USER"
    local list_mode=false
    local dry_run=false
    local force=false
    local drop_db=false

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
            -D|--database)
                database="$2"
                shift 2
                ;;
            -f|--file)
                backup_file="$2"
                shift 2
                ;;
            -H|--host)
                target_host="$2"
                shift 2
                ;;
            -p|--port)
                target_port="$2"
                shift 2
                ;;
            -U|--user)
                target_user="$2"
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
            --force)
                force=true
                shift
                ;;
            --drop-database)
                drop_db=true
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

    # 檢查必要工具
    check_tools

    # 列出備份模式
    if [ "$list_mode" = true ]; then
        if [ -z "$backup_type" ]; then
            list_backups "full"
            echo ""
            list_backups "daily"
            echo ""
            list_backups "offsite"
        else
            list_backups "$backup_type"
        fi
        exit 0
    fi

    # 如果指定了備份檔案，直接還原
    if [ -n "$backup_file" ]; then
        if [ ! -f "$backup_file" ]; then
            log_error "備份檔案不存在：$backup_file"
            exit 1
        fi
        
        log_info "========== 開始還原 =========="
        log_info "備份檔案：$backup_file"
        
        # 判斷檔案類型
        if [[ "$backup_file" == *"full_backup"* ]]; then
            restore_full_backup "$(dirname "$backup_file")" "$dry_run" "$target_host" "$target_port" "$target_user"
        else
            # 假設是單一資料庫備份
            if [ -z "$database" ]; then
                # 從檔案名稱提取資料庫名稱
                database=$(basename "$backup_file" | sed 's/_[0-9]\{8\}_[0-9]\{6\}.*//')
            fi
            restore_daily_backup "$(dirname "$backup_file")" "$database" "$dry_run" "$drop_db" "$target_host" "$target_port" "$target_user"
        fi
        
        exit 0
    fi

    # 驗證必要參數
    if [ -z "$backup_type" ] || [ -z "$backup_date" ]; then
        log_error "必須指定備份類型 (-t) 和備份日期 (-d)，或直接指定備份檔案 (-f)"
        echo ""
        show_usage
        exit 1
    fi

    # 驗證備份類型
    if [[ ! "$backup_type" =~ ^(full|daily|offsite)$ ]]; then
        log_error "無效的備份類型：$backup_type（必須是 full、daily 或 offsite）"
        exit 1
    fi

    # 驗證備份
    backup_path=$(validate_backup "$backup_type" "$backup_date")
    if [ $? -ne 0 ]; then
        exit 1
    fi

    log_info "========== 開始還原 =========="
    log_info "備份類型：$backup_type"
    log_info "備份日期：$backup_date"
    log_info "備份路徑：$backup_path"
    log_info "目標主機：$target_host:$target_port"

    # 確認操作
    if [ "$force" != "true" ] && [ "$dry_run" != "true" ]; then
        echo ""
        echo "=========================================="
        echo "⚠️  警告：此操作將會覆蓋目標資料庫的資料！"
        echo "=========================================="
        echo "備份來源：$backup_path"
        echo "目標主機：$target_host:$target_port"
        echo "目標使用者：$target_user"
        if [ -n "$database" ]; then
            echo "還原資料庫：$database"
        else
            echo "還原範圍：全部資料庫"
        fi
        if [ "$drop_db" = "true" ]; then
            echo "⚠️  將會刪除現有資料庫！"
        fi
        echo "=========================================="
        read -p "確定要繼續嗎？(yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            log_info "使用者取消還原操作"
            exit 0
        fi
    fi

    # 執行還原
    case $backup_type in
        full|offsite)
            restore_full_backup "$backup_path" "$dry_run" "$target_host" "$target_port" "$target_user"
            ;;
        daily)
            restore_daily_backup "$backup_path" "$database" "$dry_run" "$drop_db" "$target_host" "$target_port" "$target_user"
            ;;
    esac

    if [ "$dry_run" != "true" ]; then
        log_info "========== 還原操作完成 =========="
    fi
    
    # 清除密碼環境變數
    unset PGPASSWORD
}

# 執行主程式
main "$@"
