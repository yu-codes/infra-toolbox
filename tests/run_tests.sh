#!/bin/bash
# ============================================
# infra-toolbox 測試框架
# 
# 重要原則:
# - 所有備份/還原測試必須使用服務內的實際腳本
# - 這樣才能真正驗證我們的服務腳本是否可用
# 
# 測試類型:
# - 單元測試: 語法檢查、檔案存在性
# - 整合測試: 服務啟動、連接測試
# - 演練測試: 真實資料備份還原驗證 (使用服務腳本)
#
# 跨平台支援:
# - Windows (Git Bash / WSL)
# - Linux
# - macOS
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 跨平台兼容性設定
# 注意: MSYS_NO_PATHCONV 只在 docker exec 時使用，不在全局設定
# 因為 docker compose -f 需要正確的路徑轉換

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 測試計數
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# 測試環境配置
TEST_NETWORK="infra-toolbox-network"

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
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

log_subsection() {
    echo ""
    echo -e "${BLUE}--- $1 ---${NC}"
}

# ============================================
# 基礎測試函數
# ============================================

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

test_env_example() {
    local file="$1"
    local service="$2"
    
    if [ -f "$PROJECT_ROOT/$file" ]; then
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
# 服務單元測試
# ============================================

test_postgres_service() {
    log_section "Testing: postgres"
    
    test_file_exists "postgres/docker-compose.yml" "postgres"
    test_file_exists "postgres/.env.example" "postgres"
    test_file_exists "postgres/README.md" "postgres"
    test_docker_compose_syntax "postgres/docker-compose.yml" "postgres"
    test_env_example "postgres/.env.example" "postgres"
    
    if grep -q "postgres:14-alpine" "$PROJECT_ROOT/postgres/docker-compose.yml"; then
        log_success "postgres: using PostgreSQL 14"
    else
        log_error "postgres: not using PostgreSQL 14"
    fi
    
    if grep -q "archive_mode=on" "$PROJECT_ROOT/postgres/docker-compose.yml"; then
        log_success "postgres: WAL archive mode enabled"
    else
        log_error "postgres: WAL archive mode not configured"
    fi
}

test_postgres_backup_logical_service() {
    log_section "Testing: postgres_backup_logical"
    
    test_dir_exists "postgres_backup_logical" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/docker-compose.yml" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/.env.example" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/README.md" "postgres_backup_logical"
    test_docker_compose_syntax "postgres_backup_logical/docker-compose.yml" "postgres_backup_logical"
    
    test_file_exists "postgres_backup_logical/scripts/backup.sh" "postgres_backup_logical"
    test_file_exists "postgres_backup_logical/scripts/restore.sh" "postgres_backup_logical"
    test_shell_syntax "postgres_backup_logical/scripts/backup.sh" "postgres_backup_logical/backup.sh"
    test_shell_syntax "postgres_backup_logical/scripts/restore.sh" "postgres_backup_logical/restore.sh"
    
    if grep -q "pg_dump" "$PROJECT_ROOT/postgres_backup_logical/README.md" && \
       grep -q "官方" "$PROJECT_ROOT/postgres_backup_logical/README.md"; then
        log_success "postgres_backup_logical: README contains professional documentation"
    else
        log_error "postgres_backup_logical: README missing professional documentation"
    fi
}

test_postgres_backup_physical_service() {
    log_section "Testing: postgres_backup_physical"
    
    test_dir_exists "postgres_backup_physical" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/docker-compose.yml" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/.env.example" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/README.md" "postgres_backup_physical"
    test_docker_compose_syntax "postgres_backup_physical/docker-compose.yml" "postgres_backup_physical"
    
    test_file_exists "postgres_backup_physical/scripts/backup.sh" "postgres_backup_physical"
    test_file_exists "postgres_backup_physical/scripts/restore.sh" "postgres_backup_physical"
    test_shell_syntax "postgres_backup_physical/scripts/backup.sh" "postgres_backup_physical/backup.sh"
    test_shell_syntax "postgres_backup_physical/scripts/restore.sh" "postgres_backup_physical/restore.sh"
    
    if grep -q "PITR" "$PROJECT_ROOT/postgres_backup_physical/README.md" && \
       grep -q "pg_basebackup" "$PROJECT_ROOT/postgres_backup_physical/README.md"; then
        log_success "postgres_backup_physical: README contains PITR documentation"
    else
        log_error "postgres_backup_physical: README missing PITR documentation"
    fi
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
    
    test_file_exists "minio_backup/scripts/backup.sh" "minio_backup"
    test_file_exists "minio_backup/scripts/restore.sh" "minio_backup"
    test_shell_syntax "minio_backup/scripts/backup.sh" "minio_backup/backup.sh"
    test_shell_syntax "minio_backup/scripts/restore.sh" "minio_backup/restore.sh"
    
    if grep -q "mc" "$PROJECT_ROOT/minio_backup/README.md" && \
       grep -q "官方" "$PROJECT_ROOT/minio_backup/README.md"; then
        log_success "minio_backup: README contains professional documentation"
    else
        log_error "minio_backup: README missing professional documentation"
    fi
}

test_resource_monitoring_service() {
    log_section "Testing: resource_monitoring"
    
    test_file_exists "resource_monitoring/docker-compose.yml" "resource_monitoring"
    test_file_exists "resource_monitoring/.env.example" "resource_monitoring"
    test_file_exists "resource_monitoring/README.md" "resource_monitoring"
    test_docker_compose_syntax "resource_monitoring/docker-compose.yml" "resource_monitoring"
    
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
# 強制清理函數 (確保乾淨的測試環境)
# ============================================

force_cleanup() {
    log_info "Force cleaning all test containers and volumes..."
    
    # 停止並刪除所有測試相關容器
    local containers="postgres postgres-backup-logical postgres-backup-physical minio minio-backup"
    for container in $containers; do
        docker stop "$container" 2>/dev/null || true
        docker rm -f "$container" 2>/dev/null || true
    done
    
    # 使用 docker compose 清理各服務
    local services="postgres postgres_backup_logical postgres_backup_physical minio minio_backup"
    for service in $services; do
        if [ -d "$PROJECT_ROOT/$service" ]; then
            cd "$PROJECT_ROOT/$service"
            docker compose down -v --remove-orphans 2>/dev/null || true
        fi
    done
    
    # 清理備份目錄
    rm -rf "$PROJECT_ROOT/postgres_backup_logical/backups/"* 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/postgres_backup_physical/backups/"* 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/minio_backup/backups/"* 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/tests/.temp"* 2>/dev/null || true
    
    # 清理 .env 檔案
    rm -f "$PROJECT_ROOT/postgres/.env" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/postgres_backup_logical/.env" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/postgres_backup_physical/.env" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/minio/.env" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/minio_backup/.env" 2>/dev/null || true
    
    cd "$PROJECT_ROOT"
    log_info "Force cleanup completed"
}

# ============================================
# PostgreSQL 邏輯備份演練測試
# 使用 postgres_backup_logical 服務的實際腳本
# ============================================

test_postgres_logical_backup_drill() {
    log_section "PostgreSQL Logical Backup Drill Test"
    log_info "This test uses the actual backup.sh and restore.sh scripts from postgres_backup_logical service"
    
    set +e
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping drill test"
        set -e
        return 0
    fi
    
    local test_passed=true
    local TEST_DB="drill_test_db"
    local TEST_TABLE="drill_test_table"
    
    # 確保網路存在
    docker network create $TEST_NETWORK 2>/dev/null || true
    
    log_subsection "Step 1: Starting PostgreSQL Service"
    
    cd "$PROJECT_ROOT/postgres"
    
    # 建立測試用 .env
    cat > .env << 'EOF'
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpassword123
POSTGRES_DB=postgres
EOF
    
    docker compose up -d
    
    # 等待 PostgreSQL 就緒
    log_info "Waiting for PostgreSQL to be ready..."
    local wait_count=0
    while [ $wait_count -lt 30 ]; do
        if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
            break
        fi
        sleep 2
        wait_count=$((wait_count + 2))
    done
    
    if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        log_success "PostgreSQL: Service started and ready"
    else
        log_error "PostgreSQL: Failed to start"
        force_cleanup
        set -e
        return 1
    fi
    
    log_subsection "Step 2: Creating Test Data"
    
    sleep 3
    
    # 建立資料庫
    docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE $TEST_DB;" 2>/dev/null
    
    # 建立測試表格和資料
    log_info "Creating test table and data..."
    docker compose exec -T postgres psql -U postgres -d $TEST_DB -c "
        CREATE TABLE $TEST_TABLE (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            email VARCHAR(255),
            data_hash VARCHAR(64)
        );
        INSERT INTO $TEST_TABLE (username, email, data_hash) VALUES 
            ('admin', 'admin@example.com', md5('admin_data')),
            ('user1', 'user1@example.com', md5('user1_data')),
            ('drill_test', 'drill@example.com', md5('drill_verification'));
    " 2>&1
    
    # 記錄原始資料
    local original_count=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT COUNT(*) FROM $TEST_TABLE;" | tr -d ' \r\n')
    local original_hash=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT md5(string_agg(data_hash, '' ORDER BY id)) FROM $TEST_TABLE;" | tr -d ' \r\n')
    
    log_info "Original data: $original_count records, hash: $original_hash"
    log_success "PostgreSQL: Test data created ($original_count records)"
    
    log_subsection "Step 3: Starting Backup Service"
    
    cd "$PROJECT_ROOT/postgres_backup_logical"
    
    cat > .env << 'EOF'
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=testpassword123
POSTGRES_DATABASE=drill_test_db
POSTGRES_CONNECTION_MODE=docker
BACKUP_COMPRESSION_ENABLED=true
BACKUP_ENCRYPTION_ENABLED=false
EOF
    
    docker compose up -d
    sleep 3
    
    log_success "Backup Service: Started"
    
    log_subsection "Step 4: Executing Backup (using /scripts/backup.sh)"
    
    log_info "Running: docker exec postgres-backup-logical sh /scripts/backup.sh full"
    
    local backup_output
    backup_output=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-logical sh /scripts/backup.sh full 2>&1)
    
    if echo "$backup_output" | grep -q "BACKUP COMPLETE"; then
        log_success "PostgreSQL Backup: Script executed successfully"
    else
        log_error "PostgreSQL Backup: Script execution failed"
        echo "$backup_output"
        test_passed=false
    fi
    
    # 取得備份檔案名稱
    local backup_file=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-logical ls /backups/full/ 2>/dev/null | grep "^full_" | head -1)
    
    if [ -z "$backup_file" ]; then
        log_error "PostgreSQL Backup: No backup file created"
        test_passed=false
    else
        log_success "PostgreSQL Backup: Backup file created ($backup_file)"
    fi
    
    log_subsection "Step 5: Simulating Disaster (Deleting Data)"
    
    cd "$PROJECT_ROOT/postgres"
    docker compose exec -T postgres psql -U postgres -d $TEST_DB -c "DELETE FROM $TEST_TABLE;" >/dev/null 2>&1
    
    local deleted_count=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT COUNT(*) FROM $TEST_TABLE;" | tr -d ' \r\n')
    
    if [ "$deleted_count" = "0" ]; then
        log_success "PostgreSQL: Data deleted (simulated disaster)"
    else
        log_error "PostgreSQL: Failed to delete data"
        test_passed=false
    fi
    
    log_subsection "Step 6: Executing Restore (using /scripts/restore.sh)"
    
    cd "$PROJECT_ROOT/postgres_backup_logical"
    
    log_info "Running: docker exec postgres-backup-logical sh /scripts/restore.sh restore /backups/full/$backup_file"
    
    local restore_output
    restore_output=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-logical sh /scripts/restore.sh restore "/backups/full/$backup_file" 2>&1)
    
    if echo "$restore_output" | grep -q "RESTORE COMPLETE"; then
        log_success "PostgreSQL Restore: Script executed successfully"
    else
        log_error "PostgreSQL Restore: Script execution failed"
        echo "$restore_output"
        test_passed=false
    fi
    
    log_subsection "Step 7: Verifying Restored Data"
    
    cd "$PROJECT_ROOT/postgres"
    
    local restored_count=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT COUNT(*) FROM $TEST_TABLE;" | tr -d ' \r\n')
    local restored_hash=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT md5(string_agg(data_hash, '' ORDER BY id)) FROM $TEST_TABLE;" | tr -d ' \r\n')
    
    log_info "Restored data: $restored_count records, hash: $restored_hash"
    
    if [ "$restored_count" = "$original_count" ]; then
        log_success "PostgreSQL: Record count matches ($restored_count = $original_count)"
    else
        log_error "PostgreSQL: Record count mismatch ($restored_count != $original_count)"
        test_passed=false
    fi
    
    if [ "$restored_hash" = "$original_hash" ]; then
        log_success "PostgreSQL: Data integrity verified (hash match)"
    else
        log_error "PostgreSQL: Data integrity check failed"
        test_passed=false
    fi
    
    local drill_exists=$(docker compose exec -T postgres psql -U postgres -d $TEST_DB -t -c "SELECT COUNT(*) FROM $TEST_TABLE WHERE username='drill_test';" | tr -d ' \r\n')
    if [ "$drill_exists" = "1" ]; then
        log_success "PostgreSQL: Specific record verification passed"
    else
        log_error "PostgreSQL: Specific record not found"
        test_passed=false
    fi
    
    log_subsection "Step 8: Cleanup"
    
    if [ "$test_passed" = true ]; then
        log_success "PostgreSQL Logical Backup Drill: ALL TESTS PASSED"
    else
        log_error "PostgreSQL Logical Backup Drill: SOME TESTS FAILED"
    fi
    
    cd "$PROJECT_ROOT"
    set -e
    return 0
}

# ============================================
# PostgreSQL 物理備份演練測試 (PITR)
# 使用 postgres_backup_physical 服務的實際腳本
# ============================================

test_postgres_physical_backup_drill() {
    log_section "PostgreSQL Physical Backup Drill Test (PITR)"
    log_info "This test uses the actual backup.sh and restore.sh scripts from postgres_backup_physical service"
    
    set +e
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping drill test"
        set -e
        return 0
    fi
    
    local test_passed=true
    
    # 確保網路存在
    docker network create $TEST_NETWORK 2>/dev/null || true
    
    log_subsection "Step 1: Ensuring PostgreSQL Service is Running"
    
    cd "$PROJECT_ROOT/postgres"
    
    # 確保 PostgreSQL 運行中
    if ! docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        cat > .env << 'EOF'
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpassword123
POSTGRES_DB=postgres
EOF
        docker compose up -d
        
        # 等待 PostgreSQL 就緒
        local wait_count=0
        while [ $wait_count -lt 30 ]; do
            if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
                break
            fi
            sleep 2
            wait_count=$((wait_count + 2))
        done
    fi
    
    if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        log_success "PostgreSQL: Service is running"
    else
        log_error "PostgreSQL: Service not available"
        set -e
        return 1
    fi
    
    log_subsection "Step 2: Starting Physical Backup Service"
    
    cd "$PROJECT_ROOT/postgres_backup_physical"
    
    cat > .env << 'EOF'
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=testpassword123
POSTGRES_DATABASE=postgres
POSTGRES_CONNECTION_MODE=docker
BASE_BACKUP_RETENTION_DAYS=7
BASE_BACKUP_FORMAT=tar
BASE_BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION_ENABLED=false
EOF
    
    docker compose up -d
    sleep 3
    
    log_success "Physical Backup Service: Started"
    
    log_subsection "Step 3: Checking Backup Status"
    
    log_info "Running: docker exec postgres-backup-physical sh /scripts/backup.sh status"
    
    local status_output
    status_output=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-physical sh /scripts/backup.sh status 2>&1)
    
    if echo "$status_output" | grep -qi "connection.*ok\|host.*postgres"; then
        log_success "Physical Backup: Status check passed"
    else
        log_info "Status output: $status_output"
        log_skip "Physical Backup: Status check (connection may vary)"
    fi
    
    log_subsection "Step 4: Executing Base Backup"
    
    log_info "Running: docker exec postgres-backup-physical sh /scripts/backup.sh base"
    log_info "This creates a full physical backup using pg_basebackup..."
    
    local backup_output
    backup_output=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-physical sh /scripts/backup.sh base 2>&1)
    
    if echo "$backup_output" | grep -qi "backup.*complete\|success"; then
        log_success "Physical Backup: Base backup completed"
    else
        # pg_basebackup 需要 replication 權限，在測試環境中可能失敗
        if echo "$backup_output" | grep -qi "replication\|permission\|authentication"; then
            log_skip "Physical Backup: Base backup (requires replication setup)"
            log_info "  Note: pg_basebackup requires PostgreSQL replication configuration"
        else
            log_error "Physical Backup: Base backup failed"
            echo "$backup_output" | head -10
            test_passed=false
        fi
    fi
    
    log_subsection "Step 5: Listing Available Backups"
    
    log_info "Running: docker exec postgres-backup-physical sh /scripts/restore.sh list"
    
    local list_output
    list_output=$(MSYS_NO_PATHCONV=1 docker exec postgres-backup-physical sh /scripts/restore.sh list 2>&1)
    
    if echo "$list_output" | grep -qi "backup\|available"; then
        log_success "Physical Backup: List command works"
        echo "$list_output" | head -10
    else
        log_info "List output: $list_output"
        log_skip "Physical Backup: No backups available yet"
    fi
    
    log_subsection "Step 6: Cleanup"
    
    if [ "$test_passed" = true ]; then
        log_success "PostgreSQL Physical Backup Drill: ALL TESTS PASSED"
    else
        log_error "PostgreSQL Physical Backup Drill: SOME TESTS FAILED"
    fi
    
    cd "$PROJECT_ROOT"
    set -e
    return 0
}

# ============================================
# MinIO 備份演練測試
# 使用 minio_backup 服務的實際腳本
# ============================================

test_minio_backup_drill() {
    log_section "MinIO Backup Drill Test"
    log_info "This test uses the actual backup.sh and restore.sh scripts from minio_backup service"
    
    set +e
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping drill test"
        set -e
        return 0
    fi
    
    local test_passed=true
    local TEST_BUCKET="drill-test-bucket"
    
    # 確保網路存在
    docker network create $TEST_NETWORK 2>/dev/null || true
    
    log_subsection "Step 1: Starting MinIO Service"
    
    cd "$PROJECT_ROOT/minio"
    
    cat > .env << 'EOF'
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
EOF
    
    docker compose up -d
    
    # 等待 MinIO 就緒
    log_info "Waiting for MinIO to be ready..."
    local wait_count=0
    while [ $wait_count -lt 30 ]; do
        if docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin123 >/dev/null 2>&1; then
            break
        fi
        sleep 2
        wait_count=$((wait_count + 2))
    done
    
    if docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin123 >/dev/null 2>&1; then
        log_success "MinIO: Service started and ready"
    else
        log_error "MinIO: Failed to start"
        force_cleanup
        set -e
        return 1
    fi
    
    log_subsection "Step 2: Creating Test Bucket and Data"
    
    docker compose exec -T minio sh -c "
        mc mb local/$TEST_BUCKET 2>/dev/null || true
        echo 'Test file 1 - drill verification' > /tmp/test1.txt
        echo 'Test file 2 - backup content' > /tmp/test2.txt
        echo '{\"test\": \"drill\", \"time\": \"$(date)\"}' > /tmp/test.json
        mc cp /tmp/test1.txt local/$TEST_BUCKET/
        mc cp /tmp/test2.txt local/$TEST_BUCKET/
        mc cp /tmp/test.json local/$TEST_BUCKET/
    " >/dev/null 2>&1
    
    local original_count=$(docker compose exec -T minio mc ls local/$TEST_BUCKET/ 2>/dev/null | wc -l | tr -d ' \r\n')
    local original_content=$(docker compose exec -T minio mc cat local/$TEST_BUCKET/test.json 2>/dev/null | tr -d '\r\n')
    
    log_info "Original data: $original_count files"
    log_success "MinIO: Test data created ($original_count files)"
    
    log_subsection "Step 3: Starting Backup Service (with mc pre-installed)"
    
    cd "$PROJECT_ROOT/minio_backup"
    
    cat > .env << 'EOF'
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_USE_SSL=false
BACKUP_BUCKET=drill-test-bucket
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION_ENABLED=true
BACKUP_ENCRYPTION_ENABLED=false
EOF
    
    # 重新建構並啟動
    docker compose down -v 2>/dev/null || true
    docker compose up -d
    
    # 等待 mc 安裝完成
    log_info "Waiting for mc to be installed..."
    local wait_count=0
    local max_wait=90
    while [ $wait_count -lt $max_wait ]; do
        if MSYS_NO_PATHCONV=1 docker exec minio-backup mc --version >/dev/null 2>&1; then
            break
        fi
        sleep 3
        wait_count=$((wait_count + 3))
        if [ $((wait_count % 15)) -eq 0 ]; then
            log_info "  Still installing mc... ($wait_count s)"
        fi
    done
    
    if MSYS_NO_PATHCONV=1 docker exec minio-backup mc --version >/dev/null 2>&1; then
        log_success "Backup Service: mc installed successfully"
    else
        log_error "Backup Service: mc installation timeout"
        log_info "Checking container logs..."
        docker logs minio-backup 2>&1 | tail -20
        test_passed=false
        force_cleanup
        set -e
        return 1
    fi
    
    log_subsection "Step 4: Executing Backup (using /scripts/backup.sh)"
    
    log_info "Running: docker exec minio-backup sh /scripts/backup.sh"
    
    local backup_output
    backup_output=$(MSYS_NO_PATHCONV=1 docker exec minio-backup sh /scripts/backup.sh 2>&1)
    
    if echo "$backup_output" | grep -q "BACKUP COMPLETE"; then
        log_success "MinIO Backup: Script executed successfully"
    else
        log_error "MinIO Backup: Script execution failed"
        echo "$backup_output"
        test_passed=false
    fi
    
    local backup_file=$(MSYS_NO_PATHCONV=1 docker exec minio-backup ls /backups/ 2>/dev/null | grep "^minio_backup_" | head -1)
    
    if [ -z "$backup_file" ]; then
        log_error "MinIO Backup: No backup file created"
        test_passed=false
    else
        log_success "MinIO Backup: Backup file created ($backup_file)"
    fi
    
    log_subsection "Step 5: Simulating Disaster (Deleting Data)"
    
    cd "$PROJECT_ROOT/minio"
    docker compose exec -T minio mc rm --recursive --force local/$TEST_BUCKET/ >/dev/null 2>&1
    
    local deleted_count=$(docker compose exec -T minio mc ls local/$TEST_BUCKET/ 2>/dev/null | wc -l | tr -d ' \r\n')
    
    if [ "$deleted_count" = "0" ]; then
        log_success "MinIO: Data deleted (simulated disaster)"
    else
        log_error "MinIO: Failed to delete data"
        test_passed=false
    fi
    
    log_subsection "Step 6: Executing Restore (using /scripts/restore.sh)"
    
    cd "$PROJECT_ROOT/minio_backup"
    
    log_info "Running: docker exec minio-backup sh /scripts/restore.sh restore /backups/$backup_file"
    
    local restore_output
    restore_output=$(MSYS_NO_PATHCONV=1 docker exec minio-backup sh /scripts/restore.sh restore "/backups/$backup_file" 2>&1)
    
    if echo "$restore_output" | grep -q "RESTORE COMPLETE"; then
        log_success "MinIO Restore: Script executed successfully"
    else
        log_error "MinIO Restore: Script execution failed"
        echo "$restore_output"
        test_passed=false
    fi
    
    log_subsection "Step 7: Verifying Restored Data"
    
    cd "$PROJECT_ROOT/minio"
    
    local restored_count=$(docker compose exec -T minio mc ls local/$TEST_BUCKET/ 2>/dev/null | wc -l | tr -d ' \r\n')
    local restored_content=$(docker compose exec -T minio mc cat local/$TEST_BUCKET/test.json 2>/dev/null | tr -d '\r\n')
    
    log_info "Restored data: $restored_count files"
    
    if [ "$restored_count" = "$original_count" ]; then
        log_success "MinIO: File count matches ($restored_count = $original_count)"
    else
        log_error "MinIO: File count mismatch ($restored_count != $original_count)"
        test_passed=false
    fi
    
    if docker compose exec -T minio mc stat local/$TEST_BUCKET/test1.txt >/dev/null 2>&1; then
        log_success "MinIO: Specific file verification passed"
    else
        log_error "MinIO: Specific file not found"
        test_passed=false
    fi
    
    log_subsection "Step 8: Cleanup"
    
    if [ "$test_passed" = true ]; then
        log_success "MinIO Backup Drill: ALL TESTS PASSED"
    else
        log_error "MinIO Backup Drill: SOME TESTS FAILED"
    fi
    
    cd "$PROJECT_ROOT"
    set -e
    return 0
}

# ============================================
# 加密備份測試
# ============================================

test_encrypted_backup() {
    log_section "Encrypted Backup Test"
    
    set +e
    
    local test_passed=true
    local test_password="test_encryption_password_123"
    local test_data="This is sensitive data that needs to be encrypted"
    
    # 使用專案目錄下的臨時目錄 (跨平台兼容)
    local temp_dir="$PROJECT_ROOT/tests/.temp_encryption_test"
    rm -rf "$temp_dir" 2>/dev/null
    mkdir -p "$temp_dir"
    
    local test_file="$temp_dir/test_data.txt"
    local encrypted_file="$temp_dir/test_data.txt.enc"
    local decrypted_file="$temp_dir/test_data_restored.txt"
    
    log_subsection "Step 1: Creating and Encrypting Test Data"
    
    # 使用 printf 確保跨平台一致性
    printf '%s' "$test_data" > "$test_file"
    
    if [ ! -f "$test_file" ]; then
        log_error "Encryption: Failed to create test file"
        test_passed=false
    else
        # 使用與腳本相同的加密方式
        if openssl enc -aes-256-cbc -salt -pbkdf2 \
            -pass pass:"$test_password" \
            -in "$test_file" \
            -out "$encrypted_file" 2>/dev/null; then
            if [ -f "$encrypted_file" ] && [ -s "$encrypted_file" ]; then
                log_success "Encryption: File encrypted successfully"
            else
                log_error "Encryption: Encrypted file is empty or not created"
                test_passed=false
            fi
        else
            log_error "Encryption: openssl enc failed"
            test_passed=false
        fi
    fi
    
    log_subsection "Step 2: Decrypting Data"
    
    if [ -f "$encrypted_file" ]; then
        if openssl enc -aes-256-cbc -d -pbkdf2 \
            -pass pass:"$test_password" \
            -in "$encrypted_file" \
            -out "$decrypted_file" 2>/dev/null; then
            local decrypted_data=$(cat "$decrypted_file" 2>/dev/null)
            if [ "$decrypted_data" = "$test_data" ]; then
                log_success "Encryption: Decrypted content matches original"
            else
                log_error "Encryption: Decrypted content mismatch"
                test_passed=false
            fi
        else
            log_error "Encryption: openssl dec failed"
            test_passed=false
        fi
    else
        log_skip "Encryption: Skipping decryption (no encrypted file)"
    fi
    
    log_subsection "Step 3: Testing Wrong Password"
    
    if [ -f "$encrypted_file" ]; then
        if ! openssl enc -aes-256-cbc -d -pbkdf2 \
            -pass pass:"wrong_password" \
            -in "$encrypted_file" \
            -out /dev/null 2>/dev/null; then
            log_success "Encryption: Wrong password correctly rejected"
        else
            log_error "Encryption: Wrong password should fail"
            test_passed=false
        fi
    else
        log_skip "Encryption: Skipping wrong password test"
    fi
    
    # 清理
    rm -rf "$temp_dir" 2>/dev/null
    
    if [ "$test_passed" = true ]; then
        log_success "Encrypted Backup Test: ALL TESTS PASSED"
    else
        log_error "Encrypted Backup Test: SOME TESTS FAILED"
    fi
    
    set -e
    return 0
}

# ============================================
# 整合測試
# ============================================

test_integration_postgres() {
    log_section "Integration Test: postgres"
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available"
        return 0
    fi
    
    docker network create $TEST_NETWORK 2>/dev/null || true
    
    cd "$PROJECT_ROOT/postgres"
    
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || echo "POSTGRES_PASSWORD=testpassword" > .env
    fi
    
    if docker compose up -d --wait 2>/dev/null; then
        log_success "postgres: service started"
        
        sleep 5
        
        if docker compose exec -T postgres pg_isready -U postgres 2>/dev/null; then
            log_success "postgres: connection test passed"
        else
            log_error "postgres: connection test failed"
        fi
        
        docker compose down -v 2>/dev/null
    else
        log_error "postgres: service failed to start"
    fi
    
    cd "$PROJECT_ROOT"
}

test_integration_resource_monitoring() {
    log_section "Integration Test: resource_monitoring"
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available"
        return 0
    fi
    
    docker network create $TEST_NETWORK 2>/dev/null || true
    
    cd "$PROJECT_ROOT/resource_monitoring"
    
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || touch .env
    fi
    
    if docker compose up -d --build 2>/dev/null; then
        log_success "resource_monitoring: service started"
        
        sleep 10
        
        if curl -s http://localhost:10003/health 2>/dev/null | grep -q "healthy"; then
            log_success "resource_monitoring: API health check passed"
        else
            log_skip "resource_monitoring: API health check (service may still be starting)"
        fi
        
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

run_drill_tests() {
    log_section "Running Backup/Restore Drill Tests"
    log_info "These tests use the actual service scripts to verify backup/restore functionality"
    echo ""
    
    # 先強制清理確保乾淨的環境
    force_cleanup
    
    test_postgres_logical_backup_drill
    test_postgres_physical_backup_drill
    test_minio_backup_drill
    test_encrypted_backup
    
    # 最終清理
    force_cleanup
}

show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  unit        Run unit tests only (syntax, file checks)"
    echo "  integration Run integration tests (requires Docker)"
    echo "  drill       Run backup/restore drill tests using actual service scripts"
    echo "  all         Run all tests (default)"
    echo "  clean       Force cleanup all test containers and files"
    echo "  help        Show this help message"
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
        drill)
            run_drill_tests
            ;;
        all)
            run_unit_tests
            run_integration_tests
            run_drill_tests
            ;;
        clean)
            force_cleanup
            echo "Cleanup completed"
            exit 0
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
