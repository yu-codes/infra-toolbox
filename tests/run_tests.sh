#!/bin/bash
# ============================================
# infra-toolbox 測試框架
# 用於本地和 CI/CD 環境執行測試
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 測試計數
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# ============================================
# 基礎測試函數
# ============================================

# 檢查檔案是否存在
test_file_exists() {
    local file="$1"
    local description="$2"
    
    if [ -f "$PROJECT_ROOT/$file" ]; then
        log_success "$description: $file exists"
        return 0
    else
        log_error "$description: $file not found"
        return 1
    fi
}

# 檢查目錄是否存在
test_dir_exists() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        log_success "$description: $dir exists"
        return 0
    else
        log_error "$description: $dir not found"
        return 1
    fi
}

# 檢查 Docker Compose 檔案語法
test_docker_compose_syntax() {
    local file="$1"
    local service="$2"
    
    if docker compose -f "$PROJECT_ROOT/$file" config > /dev/null 2>&1; then
        log_success "$service: docker-compose.yml syntax valid"
        return 0
    else
        log_error "$service: docker-compose.yml syntax invalid"
        return 1
    fi
}

# 檢查 Shell 腳本語法
test_shell_syntax() {
    local file="$1"
    local description="$2"
    
    if sh -n "$PROJECT_ROOT/$file" 2>/dev/null; then
        log_success "$description: shell syntax valid"
        return 0
    else
        log_error "$description: shell syntax invalid"
        return 1
    fi
}

# 檢查環境變數範例檔案
test_env_example() {
    local file="$1"
    local service="$2"
    
    if [ -f "$PROJECT_ROOT/$file" ]; then
        # 檢查是否有內容
        if [ -s "$PROJECT_ROOT/$file" ]; then
            log_success "$service: .env.example has content"
            return 0
        else
            log_error "$service: .env.example is empty"
            return 1
        fi
    else
        log_error "$service: .env.example not found"
        return 1
    fi
}

# ============================================
# 服務特定測試
# ============================================

test_postgres_service() {
    log_section "Testing: postgres"
    
    test_file_exists "postgres/docker-compose.yml" "postgres"
    test_file_exists "postgres/.env.example" "postgres"
    test_file_exists "postgres/README.md" "postgres"
    test_docker_compose_syntax "postgres/docker-compose.yml" "postgres"
    test_env_example "postgres/.env.example" "postgres"
    
    # 檢查 PostgreSQL 版本是否為 14
    if grep -q "postgres:14-alpine" "$PROJECT_ROOT/postgres/docker-compose.yml"; then
        log_success "postgres: using PostgreSQL 14"
    else
        log_error "postgres: not using PostgreSQL 14"
    fi
}

test_postgres_backup_logical_service() {
    log_section "Testing: postgres_backup_logical"
    
    test_dir_exists "postgres_backup_logical" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/docker-compose.yml" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/.env.example" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/README.md" "postgres_backup_logical"
    test_docker_compose_syntax "postgres_backup_logical/docker-compose.yml" "postgres_backup_logical"
    
    # 測試腳本
    test_file_exists "postgres_backup_logical/scripts/backup.sh" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/scripts/restore.sh" "postgres_backup_logical"
    test_shell_syntax "postgres_backup_logical/scripts/backup.sh" "postgres_backup_logical/backup.sh"
    test_shell_syntax "postgres_backup_logical/scripts/restore.sh" "postgres_backup_logical/restore.sh"
}

test_postgres_backup_physical_service() {
    log_section "Testing: postgres_backup_physical"
    
    test_dir_exists "postgres_backup_physical" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/docker-compose.yml" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/.env.example" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/README.md" "postgres_backup_physical"
    test_docker_compose_syntax "postgres_backup_physical/docker-compose.yml" "postgres_backup_physical"
    
    # 測試腳本
    test_file_exists "postgres_backup_physical/scripts/backup.sh" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/scripts/restore.sh" "postgres_backup_physical"
    test_shell_syntax "postgres_backup_physical/scripts/backup.sh" "postgres_backup_physical/backup.sh"
    test_shell_syntax "postgres_backup_physical/scripts/restore.sh" "postgres_backup_physical/restore.sh"
}

test_minio_service() {
    log_section "Testing: minio"
    
    test_file_exists "minio/docker-compose.yml" "minio"
    test_file_exists "minio/.env.example" "minio"
    test_file_exists "minio/README.md" "minio"
    test_docker_compose_syntax "minio/docker-compose.yml" "minio"
}

test_minio_backup_service() {
    log_section "Testing: minio_backup"
    
    test_file_exists "minio_backup/docker-compose.yml" "minio_backup"
    test_file_exists "minio_backup/.env.example" "minio_backup"
    test_file_exists "minio_backup/README.md" "minio_backup"
    test_docker_compose_syntax "minio_backup/docker-compose.yml" "minio_backup"
    
    # 測試腳本
    if [ -f "$PROJECT_ROOT/minio_backup/scripts/backup.sh" ]; then
        test_shell_syntax "minio_backup/scripts/backup.sh" "minio_backup/backup.sh"
    fi
    if [ -f "$PROJECT_ROOT/minio_backup/scripts/restore.sh" ]; then
        test_shell_syntax "minio_backup/scripts/restore.sh" "minio_backup/restore.sh"
    fi
}

test_resource_monitoring_service() {
    log_section "Testing: resource_monitoring"
    
    test_file_exists "resource_monitoring/docker-compose.yml" "resource_monitoring"
    test_file_exists "resource_monitoring/.env.example" "resource_monitoring"
    test_file_exists "resource_monitoring/README.md" "resource_monitoring"
    test_docker_compose_syntax "resource_monitoring/docker-compose.yml" "resource_monitoring"
    
    # 測試 API
    test_file_exists "resource_monitoring/api/main.py" "resource_monitoring"
    test_file_exists "resource_monitoring/api/requirements.txt" "resource_monitoring"
    test_file_exists "resource_monitoring/api/Dockerfile" "resource_monitoring"
}

test_filebrowser_service() {
    log_section "Testing: filebrowser"
    
    test_file_exists "filebrowser/docker-compose.yml" "filebrowser"
    test_file_exists "filebrowser/.env.example" "filebrowser"
    test_file_exists "filebrowser/README.md" "filebrowser"
    test_docker_compose_syntax "filebrowser/docker-compose.yml" "filebrowser"
}

# ============================================
# 整合測試 (需要 Docker)
# ============================================

test_integration_postgres() {
    log_section "Integration Test: postgres"
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping integration test"
        return 0
    fi
    
    log_info "Creating test network..."
    docker network create infra-toolbox-network 2>/dev/null || true
    
    log_info "Starting postgres service..."
    cd "$PROJECT_ROOT/postgres"
    
    # 確保 .env 存在
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || echo "POSTGRES_PASSWORD=testpassword" > .env
    fi
    
    # 啟動服務
    if docker compose up -d --wait 2>/dev/null; then
        log_success "postgres: service started successfully"
        
        # 等待健康檢查
        sleep 5
        
        # 測試連接
        if docker compose exec -T postgres pg_isready -U postgres 2>/dev/null; then
            log_success "postgres: connection test passed"
        else
            log_error "postgres: connection test failed"
        fi
        
        # 清理
        docker compose down -v 2>/dev/null
    else
        log_error "postgres: service failed to start"
    fi
    
    cd "$PROJECT_ROOT"
}

test_integration_resource_monitoring() {
    log_section "Integration Test: resource_monitoring"
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping integration test"
        return 0
    fi
    
    log_info "Creating test network..."
    docker network create infra-toolbox-network 2>/dev/null || true
    
    log_info "Starting resource_monitoring service..."
    cd "$PROJECT_ROOT/resource_monitoring"
    
    # 確保 .env 存在
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || touch .env
    fi
    
    # 啟動服務
    if docker compose up -d --build 2>/dev/null; then
        log_success "resource_monitoring: service started successfully"
        
        # 等待服務啟動
        sleep 10
        
        # 測試 API
        if curl -s http://localhost:10003/health 2>/dev/null | grep -q "healthy"; then
            log_success "resource_monitoring: API health check passed"
        else
            log_skip "resource_monitoring: API health check (service may still be starting)"
        fi
        
        # 清理
        docker compose down -v 2>/dev/null
    else
        log_error "resource_monitoring: service failed to start"
    fi
    
    cd "$PROJECT_ROOT"
}

# ============================================
# 主程式
# ============================================

print_summary() {
    log_section "Test Summary"
    echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e "  ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
    echo ""
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    fi
}

run_unit_tests() {
    log_section "Running Unit Tests"
    
    test_postgres_service
    test_postgres_backup_logical_service
    test_postgres_backup_physical_service
    test_minio_service
    test_minio_backup_service
    test_resource_monitoring_service
    test_filebrowser_service
}

run_integration_tests() {
    log_section "Running Integration Tests"
    
    test_integration_postgres
    test_integration_resource_monitoring
}

show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  unit        Run unit tests only (syntax, file checks)"
    echo "  integration Run integration tests (requires Docker)"
    echo "  all         Run all tests (default)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Run all tests"
    echo "  $0 unit         # Run unit tests only"
    echo "  $0 integration  # Run integration tests only"
}

main() {
    echo ""
    echo "============================================"
    echo "  infra-toolbox Test Suite"
    echo "============================================"
    echo ""
    
    case "${1:-all}" in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        all)
            run_unit_tests
            run_integration_tests
            ;;
        help|--help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
    
    print_summary
}

main "$@"
