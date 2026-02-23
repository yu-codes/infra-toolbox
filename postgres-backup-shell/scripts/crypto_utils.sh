#!/bin/bash

# ============================================================
# 加密與壓縮通用工具函數
# ============================================================

# 壓縮檔案
compress_file() {
    local input_file=$1
    local compression_type=${2:-$COMPRESSION_TYPE}
    local compression_level=${3:-$COMPRESSION_LEVEL}
    local output_file=""
    
    case $compression_type in
        gzip)
            output_file="${input_file}.gz"
            if gzip -${compression_level} -c "$input_file" > "$output_file"; then
                rm -f "$input_file"
                echo "$output_file"
                return 0
            fi
            ;;
        bzip2)
            output_file="${input_file}.bz2"
            if bzip2 -${compression_level} -c "$input_file" > "$output_file"; then
                rm -f "$input_file"
                echo "$output_file"
                return 0
            fi
            ;;
        xz)
            output_file="${input_file}.xz"
            if xz -${compression_level} -c "$input_file" > "$output_file"; then
                rm -f "$input_file"
                echo "$output_file"
                return 0
            fi
            ;;
        none)
            echo "$input_file"
            return 0
            ;;
        *)
            log_error "不支援的壓縮類型: $compression_type"
            return 1
            ;;
    esac
    
    return 1
}

# 解壓縮檔案
decompress_file() {
    local input_file=$1
    local output_file="${input_file}"
    
    # 根據副檔名判斷壓縮類型
    if [[ "$input_file" == *.gz ]]; then
        output_file="${input_file%.gz}"
        gunzip -c "$input_file" > "$output_file" && rm -f "$input_file"
    elif [[ "$input_file" == *.bz2 ]]; then
        output_file="${input_file%.bz2}"
        bunzip2 -c "$input_file" > "$output_file" && rm -f "$input_file"
    elif [[ "$input_file" == *.xz ]]; then
        output_file="${input_file%.xz}"
        unxz -c "$input_file" > "$output_file" && rm -f "$input_file"
    fi
    
    echo "$output_file"
}

# 加密檔案
encrypt_file() {
    local input_file=$1
    local encryption_method=${2:-$ENCRYPTION_METHOD}
    local password=${3:-$ENCRYPTION_PASSWORD}
    local key_file=${4:-$ENCRYPTION_KEY_FILE}
    local output_file="${input_file}.enc"
    
    # 優先使用金鑰檔案
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        password=$(cat "$key_file")
    fi
    
    if [ -z "$password" ] && [ "$encryption_method" != "gpg" ]; then
        log_error "未設定加密密碼或金鑰檔案"
        return 1
    fi
    
    case $encryption_method in
        openssl-aes256)
            if openssl enc -aes-256-cbc -salt -pbkdf2 -in "$input_file" -out "$output_file" -pass pass:"$password"; then
                rm -f "$input_file"
                echo "$output_file"
                return 0
            fi
            ;;
        gpg)
            if [ -n "$GPG_RECIPIENT" ]; then
                # 使用公鑰加密（不需要密碼）
                if gpg --encrypt --recipient "$GPG_RECIPIENT" --output "$output_file" "$input_file"; then
                    rm -f "$input_file"
                    echo "$output_file"
                    return 0
                fi
            elif [ -n "$password" ]; then
                # 使用對稱加密（需要密碼）
                if echo "$password" | gpg --batch --yes --passphrase-fd 0 --symmetric --cipher-algo AES256 --output "$output_file" "$input_file"; then
                    rm -f "$input_file"
                    echo "$output_file"
                    return 0
                fi
            else
                log_error "GPG 加密需要設定 GPG_RECIPIENT 或密碼"
                return 1
            fi
            ;;
        *)
            log_error "不支援的加密方式: $encryption_method"
            return 1
            ;;
    esac
    
    return 1
}

# 解密檔案
decrypt_file() {
    local input_file=$1
    local encryption_method=${2:-$ENCRYPTION_METHOD}
    local password=${3:-$ENCRYPTION_PASSWORD}
    local key_file=${4:-$ENCRYPTION_KEY_FILE}
    local output_file="${input_file%.enc}"
    
    # 優先使用金鑰檔案
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        password=$(cat "$key_file")
    fi
    
    if [ -z "$password" ] && [ "$encryption_method" != "gpg" ]; then
        log_error "未設定解密密碼或金鑰檔案"
        return 1
    fi
    
    case $encryption_method in
        openssl-aes256)
            if openssl enc -aes-256-cbc -d -pbkdf2 -in "$input_file" -out "$output_file" -pass pass:"$password"; then
                rm -f "$input_file"
                echo "$output_file"
                return 0
            fi
            ;;
        gpg)
            if [ -n "$password" ]; then
                # 使用密碼解密
                if echo "$password" | gpg --batch --yes --passphrase-fd 0 --decrypt --output "$output_file" "$input_file"; then
                    rm -f "$input_file"
                    echo "$output_file"
                    return 0
                fi
            else
                # 使用私鑰解密（自動）
                if gpg --decrypt --output "$output_file" "$input_file"; then
                    rm -f "$input_file"
                    echo "$output_file"
                    return 0
                fi
            fi
            ;;
        *)
            log_error "不支援的解密方式: $encryption_method"
            return 1
            ;;
    esac
    
    return 1
}

# 壓縮並加密檔案（一步完成）
compress_and_encrypt() {
    local input_file=$1
    local final_file="$input_file"
    
    # 步驟 1：壓縮
    if [ "${COMPRESSION_TYPE:-gzip}" != "none" ]; then
        log_info "壓縮檔案: $(basename "$input_file")"
        final_file=$(compress_file "$final_file" "$COMPRESSION_TYPE" "$COMPRESSION_LEVEL")
        if [ $? -ne 0 ]; then
            log_error "壓縮失敗"
            return 1
        fi
        log_info "壓縮完成: $(basename "$final_file")"
    fi
    
    # 步驟 2：加密
    if [ "${ENABLE_ENCRYPTION:-false}" = "true" ]; then
        log_info "加密檔案: $(basename "$final_file")"
        final_file=$(encrypt_file "$final_file" "$ENCRYPTION_METHOD" "$ENCRYPTION_PASSWORD" "$ENCRYPTION_KEY_FILE")
        if [ $? -ne 0 ]; then
            log_error "加密失敗"
            return 1
        fi
        log_info "加密完成: $(basename "$final_file")"
    fi
    
    echo "$final_file"
    return 0
}

# 解密並解壓縮檔案（一步完成）
decrypt_and_decompress() {
    local input_file=$1
    local final_file="$input_file"
    
    # 步驟 1：解密
    if [[ "$input_file" == *.enc ]]; then
        log_info "解密檔案: $(basename "$input_file")"
        final_file=$(decrypt_file "$final_file" "$ENCRYPTION_METHOD" "$ENCRYPTION_PASSWORD" "$ENCRYPTION_KEY_FILE")
        if [ $? -ne 0 ]; then
            log_error "解密失敗"
            return 1
        fi
        log_info "解密完成: $(basename "$final_file")"
    fi
    
    # 步驟 2：解壓縮
    if [[ "$final_file" == *.gz ]] || [[ "$final_file" == *.bz2 ]] || [[ "$final_file" == *.xz ]]; then
        log_info "解壓縮檔案: $(basename "$final_file")"
        final_file=$(decompress_file "$final_file")
        if [ $? -ne 0 ]; then
            log_error "解壓縮失敗"
            return 1
        fi
        log_info "解壓縮完成: $(basename "$final_file")"
    fi
    
    echo "$final_file"
    return 0
}

# 檢查必要的加密工具是否安裝
check_crypto_tools() {
    local encryption_method=${1:-$ENCRYPTION_METHOD}
    local compression_type=${2:-$COMPRESSION_TYPE}
    
    # 檢查壓縮工具
    case $compression_type in
        gzip)
            if ! command -v gzip &> /dev/null; then
                log_error "gzip 未安裝"
                return 1
            fi
            ;;
        bzip2)
            if ! command -v bzip2 &> /dev/null; then
                log_error "bzip2 未安裝"
                return 1
            fi
            ;;
        xz)
            if ! command -v xz &> /dev/null; then
                log_error "xz 未安裝"
                return 1
            fi
            ;;
    esac
    
    # 檢查加密工具
    if [ "${ENABLE_ENCRYPTION:-false}" = "true" ]; then
        case $encryption_method in
            openssl-aes256)
                if ! command -v openssl &> /dev/null; then
                    log_error "openssl 未安裝"
                    return 1
                fi
                ;;
            gpg)
                if ! command -v gpg &> /dev/null; then
                    log_error "gpg 未安裝"
                    return 1
                fi
                ;;
        esac
    fi
    
    return 0
}
