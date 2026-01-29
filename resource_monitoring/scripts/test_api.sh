#!/bin/bash
# Resource Monitoring API 測試腳本
# 測試 JWT 啟用和關閉機制

API_URL="http://localhost:10003"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "Resource Monitoring API 測試"
echo "======================================"

# 等待 API 就緒
wait_for_api() {
    echo "等待 API 就緒..."
    for i in {1..30}; do
        if curl -s "$API_URL/health" > /dev/null 2>&1; then
            echo "✓ API 已就緒"
            return 0
        fi
        sleep 1
    done
    echo "✗ API 未能在 30 秒內就緒"
    return 1
}

# 測試無需認證的端點
test_public_endpoints() {
    echo ""
    echo "--- 測試公開端點 ---"
    
    echo -n "GET /health: "
    response=$(curl -s "$API_URL/health")
    if echo "$response" | grep -q "healthy"; then
        echo "✓ 通過"
    else
        echo "✗ 失敗: $response"
        return 1
    fi

    echo -n "GET /: "
    response=$(curl -s "$API_URL/")
    if echo "$response" | grep -q "Resource Monitoring API"; then
        echo "✓ 通過"
    else
        echo "✗ 失敗: $response"
        return 1
    fi
}

# 測試需要認證的端點（JWT 啟用時）
test_protected_endpoints_with_jwt() {
    echo ""
    echo "--- 測試受保護端點 (JWT 啟用) ---"
    
    # 取得 JWT token（從檔案讀取或使用環境變數中的密鑰）
    TOKEN_FILE="$COMPOSE_DIR/data/.jwt_token_info.json"
    if [ -f "$TOKEN_FILE" ]; then
        TOKEN=$(cat "$TOKEN_FILE" | grep -o '"sample_token": "[^"]*"' | cut -d'"' -f4)
    else
        echo "找不到 token 檔案，使用環境變數中的密鑰"
        TOKEN=$JWT_SECRET_KEY
    fi

    if [ -z "$TOKEN" ]; then
        echo "✗ 無法取得 JWT token"
        return 1
    fi

    echo "使用 Token: ${TOKEN:0:30}..."

    # 無 token 應該失敗
    echo -n "GET /system-metrics (無 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/system-metrics")
    if [ "$response" = "401" ]; then
        echo "✓ 正確拒絕 (401)"
    else
        echo "✗ 預期 401，實際 $response"
    fi

    # 有 token 應該成功
    echo -n "GET /system-metrics (有 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/system-metrics")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi

    # 測試其他受保護端點
    echo -n "GET /cpu-config (有 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/cpu-config")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi

    echo -n "GET /log-status (有 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/log-status")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi
}

# 測試需要認證的端點（JWT 關閉時）
test_protected_endpoints_without_jwt() {
    echo ""
    echo "--- 測試受保護端點 (JWT 關閉) ---"
    
    # 無 token 也應該成功
    echo -n "GET /system-metrics (無 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/system-metrics")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi

    echo -n "GET /cpu-config (無 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/cpu-config")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi

    echo -n "GET /log-status (無 token): "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/log-status")
    if [ "$response" = "200" ]; then
        echo "✓ 通過 (200)"
    else
        echo "✗ 預期 200，實際 $response"
    fi
}

# 檢查 JWT 狀態
check_jwt_status() {
    response=$(curl -s "$API_URL/health")
    if echo "$response" | grep -q '"jwt_enabled":true'; then
        return 0  # JWT 啟用
    else
        return 1  # JWT 關閉
    fi
}

# 主測試流程
main() {
    wait_for_api || exit 1
    test_public_endpoints || exit 1

    if check_jwt_status; then
        echo ""
        echo "JWT 狀態: 啟用"
        test_protected_endpoints_with_jwt
    else
        echo ""
        echo "JWT 狀態: 關閉"
        test_protected_endpoints_without_jwt
    fi

    echo ""
    echo "======================================"
    echo "測試完成"
    echo "======================================"
}

main "$@"
