#!/usr/bin/env bash
# =============================================================================
# run_tests.sh - GeoServer API 完整整合測試腳本
#
# 執行流程：
#   1. 在 geoserver/ 目錄下建置並啟動容器
#   2. 等待 GeoServer 健康檢查通過、API 就緒
#   3. 安裝測試依賴並執行 pytest
#   4. 輸出結果摘要
#
# 使用方式：
#   cd geoserver/
#   bash tests/run_tests.sh
#
# 環境需求：
#   - Docker + Docker Compose
#   - Python 3.10+
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

API_URL="http://localhost:8000"
GEOSERVER_URL="http://localhost:8080/geoserver/web/"
MAX_WAIT=180   # 最長等待秒數
INTERVAL=5

echo "================================================================"
echo " GeoServer API 整合測試"
echo "================================================================"
echo ""

# ------------------------------------------------------------------------------
# 步驟 1：啟動容器
# ------------------------------------------------------------------------------
echo "[1/4] 建置並啟動容器..."
cd "${PROJECT_DIR}"
docker compose down --remove-orphans 2>/dev/null || true
docker compose build
docker compose up -d

# ------------------------------------------------------------------------------
# 步驟 2：等待 GeoServer 就緒
# ------------------------------------------------------------------------------
echo ""
echo "[2/4] 等待 GeoServer 就緒（最長 ${MAX_WAIT}s）..."
elapsed=0
until curl -sf "${GEOSERVER_URL}" > /dev/null 2>&1; do
    if [ "${elapsed}" -ge "${MAX_WAIT}" ]; then
        echo "❌ 逾時：GeoServer 在 ${MAX_WAIT}s 內未就緒"
        docker compose logs geoserver | tail -30
        docker compose down
        exit 1
    fi
    printf "  (%ds) 等待 GeoServer...\n" "${elapsed}"
    sleep "${INTERVAL}"
    elapsed=$((elapsed + INTERVAL))
done
echo "  ✅ GeoServer 已就緒"

# 等待 API 就緒
echo ""
echo "  等待 API 服務就緒..."
elapsed=0
until curl -sf "${API_URL}/health" > /dev/null 2>&1; do
    if [ "${elapsed}" -ge 60 ]; then
        echo "❌ 逾時：API 在 60s 內未就緒"
        docker compose logs api | tail -20
        docker compose down
        exit 1
    fi
    printf "  (%ds) 等待 API...\n" "${elapsed}"
    sleep "${INTERVAL}"
    elapsed=$((elapsed + INTERVAL))
done
echo "  ✅ API 已就緒"

# ------------------------------------------------------------------------------
# 步驟 3：安裝測試依賴並執行測試
# ------------------------------------------------------------------------------
echo ""
echo "[3/4] 安裝測試依賴..."
pip install -q -r "${SCRIPT_DIR}/requirements.txt"

echo ""
echo "[4/4] 執行 pytest..."
echo "----------------------------------------------------------------"
cd "${SCRIPT_DIR}"
pytest test_geoserver_api.py -v --tb=short 2>&1
TEST_EXIT_CODE=$?

# ------------------------------------------------------------------------------
# 步驟 4：清理與摘要
# ------------------------------------------------------------------------------
echo ""
echo "================================================================"
cd "${PROJECT_DIR}"
if [ "${TEST_EXIT_CODE}" -eq 0 ]; then
    echo " ✅ 所有測試通過"
else
    echo " ❌ 有測試失敗（exit code: ${TEST_EXIT_CODE}）"
    echo ""
    echo " 除錯指令："
    echo "   docker compose logs geoserver | tail -50"
    echo "   docker compose logs api | tail -50"
fi
echo "================================================================"
echo ""
echo " 容器仍在運行，可使用以下指令停止："
echo "   cd ${PROJECT_DIR} && docker compose down"
echo ""

exit "${TEST_EXIT_CODE}"
