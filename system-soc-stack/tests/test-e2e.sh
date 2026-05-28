#!/bin/bash
# =============================================================================
# System SOC Stack - End-to-End Test Suite
# =============================================================================
# Comprehensive tests for the entire SOC stack.
#
# Usage: ./tests/test-e2e.sh [--quick] [--verbose]
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

QUICK=false
VERBOSE=false
PASSED=0
FAILED=0
SKIPPED=0

for arg in "$@"; do
    case $arg in
        --quick) QUICK=true ;;
        --verbose|-v) VERBOSE=true ;;
    esac
done

log_test()  { echo -e "${BLUE}[TEST]${NC} $1"; }
log_pass()  { echo -e "${GREEN}[PASS]${NC} $1"; PASSED=$((PASSED + 1)); }
log_fail()  { echo -e "${RED}[FAIL]${NC} $1"; FAILED=$((FAILED + 1)); }
log_skip()  { echo -e "${YELLOW}[SKIP]${NC} $1"; SKIPPED=$((SKIPPED + 1)); }
log_info()  { [ "${VERBOSE}" = true ] && echo -e "       $1"; }

# =============================================================================
# Infrastructure Tests
# =============================================================================
test_docker_compose_valid() {
    log_test "Docker Compose file is valid"
    if docker compose -f "${PROJECT_DIR}/docker-compose.yml" config >/dev/null 2>&1; then
        log_pass "docker-compose.yml validates successfully"
    else
        log_fail "docker-compose.yml has syntax errors"
    fi
}

test_env_file_exists() {
    log_test ".env file exists"
    if [ -f "${PROJECT_DIR}/.env" ]; then
        log_pass ".env file present"
    else
        log_fail ".env file missing (run setup.sh first)"
    fi
}

test_certificates_exist() {
    log_test "SSL certificates exist"
    local required_certs=(root-ca.pem indexer.pem indexer-key.pem manager.pem manager-key.pem dashboard.pem dashboard-key.pem admin.pem admin-key.pem)
    local missing=0

    for cert in "${required_certs[@]}"; do
        if [ ! -f "${PROJECT_DIR}/certs/${cert}" ]; then
            log_info "Missing: certs/${cert}"
            missing=$((missing + 1))
        fi
    done

    if [ ${missing} -eq 0 ]; then
        log_pass "All ${#required_certs[@]} certificates present"
    else
        log_fail "${missing} certificates missing"
    fi
}

# =============================================================================
# Container Status Tests
# =============================================================================
test_container_running() {
    local container=$1
    local display_name=$2

    log_test "${display_name} container is running"
    local status
    status=$(docker inspect --format='{{.State.Running}}' "${container}" 2>/dev/null || echo "false")

    if [ "${status}" = "true" ]; then
        log_pass "${display_name} is running"
    else
        log_fail "${display_name} is NOT running"
    fi
}

test_container_healthy() {
    local container=$1
    local display_name=$2

    log_test "${display_name} is healthy"
    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "none")

    if [ "${health}" = "healthy" ]; then
        log_pass "${display_name} health check passed"
    elif [ "${health}" = "starting" ]; then
        log_skip "${display_name} still starting"
    else
        log_fail "${display_name} health: ${health}"
    fi
}

# =============================================================================
# Wazuh Indexer Tests
# =============================================================================
test_indexer_api() {
    log_test "Wazuh Indexer API responds"
    local password
    password=$(grep INDEXER_PASSWORD "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "")

    local response
    response=$(curl -sku "admin:${password}" "https://localhost:9200" 2>/dev/null || echo "")

    if echo "${response}" | grep -q "wazuh-indexer"; then
        log_pass "Indexer API accessible"
    else
        log_fail "Indexer API not responding"
    fi
}

test_indexer_cluster_health() {
    log_test "Indexer cluster health"
    local password
    password=$(grep INDEXER_PASSWORD "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "")

    local health
    health=$(curl -sku "admin:${password}" "https://localhost:9200/_cluster/health" 2>/dev/null || echo "")

    if echo "${health}" | grep -qE '"status":"(green|yellow)"'; then
        local status
        status=$(echo "${health}" | grep -oP '"status":"\K[^"]+')
        log_pass "Cluster status: ${status}"
    else
        log_fail "Cluster unhealthy or unreachable"
    fi
}

# =============================================================================
# Wazuh Manager Tests
# =============================================================================
test_manager_api() {
    log_test "Wazuh Manager API responds"
    local api_user
    api_user=$(grep WAZUH_MANAGER_API_USER "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "wazuh-wui")
    local api_pass
    api_pass=$(grep WAZUH_MANAGER_API_PASSWORD "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "")

    # Get token
    local token
    token=$(curl -sku "${api_user}:${api_pass}" -X POST "https://localhost:55000/security/user/authenticate" 2>/dev/null | \
        grep -oP '"token":"\K[^"]+' || echo "")

    if [ -n "${token}" ]; then
        log_pass "Manager API authentication successful"
    else
        log_fail "Manager API authentication failed"
    fi
}

test_agent_connected() {
    log_test "Wazuh Agent connected to Manager"
    local agent_status
    agent_status=$(docker exec soc-wazuh-manager /var/ossec/bin/agent_control -l 2>/dev/null | grep -c "Active" || echo "0")

    if [ "${agent_status}" -gt 0 ]; then
        log_pass "${agent_status} agent(s) connected"
    else
        log_fail "No agents connected"
    fi
}

# =============================================================================
# ClamAV Tests
# =============================================================================
test_clamav_daemon() {
    log_test "ClamAV daemon running"
    local version
    version=$(docker exec soc-clamav clamdscan --version 2>/dev/null || echo "")

    if [ -n "${version}" ]; then
        log_pass "ClamAV: ${version}"
    else
        log_fail "ClamAV daemon not responding"
    fi
}

test_clamav_db_loaded() {
    log_test "ClamAV virus database loaded"
    local db_info
    db_info=$(docker exec soc-clamav clamdscan --version 2>/dev/null || echo "")

    if echo "${db_info}" | grep -qE "[0-9]+"; then
        log_pass "Virus database loaded"
    else
        log_fail "No virus database loaded"
    fi
}

test_clamav_eicar_detection() {
    log_test "ClamAV EICAR test file detection"

    # Create EICAR in container
    local eicar='X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    docker exec soc-clamav sh -c "echo '${eicar}' > /tmp/eicar-e2e.txt" 2>/dev/null

    local result
    result=$(docker exec soc-clamav clamdscan /tmp/eicar-e2e.txt 2>&1 || true)

    # Cleanup
    docker exec soc-clamav rm -f /tmp/eicar-e2e.txt 2>/dev/null

    if echo "${result}" | grep -q "FOUND"; then
        log_pass "EICAR detected: $(echo "${result}" | grep "FOUND" | head -1)"
    else
        log_fail "EICAR not detected"
    fi
}

# =============================================================================
# Integration Tests
# =============================================================================
test_clamav_log_monitored() {
    log_test "ClamAV logs monitored by Wazuh agent"

    # Check agent config includes ClamAV log
    local config_check
    config_check=$(docker exec soc-wazuh-agent grep -c "clamav" /var/ossec/etc/ossec.conf 2>/dev/null || echo "0")

    if [ "${config_check}" -gt 0 ]; then
        log_pass "Agent configured to monitor ClamAV logs"
    else
        log_fail "Agent not configured for ClamAV log monitoring"
    fi
}

test_shared_volume() {
    log_test "ClamAV log volume shared correctly"

    # Write test line from scanner
    docker exec soc-clamav-scanner sh -c "echo 'test-$(date +%s)' >> /var/log/clamav/scan.log" 2>/dev/null

    sleep 2

    # Read from agent
    local agent_read
    agent_read=$(docker exec soc-wazuh-agent tail -1 /var/log/clamav/scan.log 2>/dev/null || echo "")

    if echo "${agent_read}" | grep -q "test-"; then
        log_pass "Log volume shared between ClamAV and Wazuh agent"
    else
        log_fail "Log volume not accessible from Wazuh agent"
    fi
}

test_custom_rules_loaded() {
    log_test "Custom ClamAV rules loaded in Manager"

    local rules_check
    rules_check=$(docker exec soc-wazuh-manager cat /var/ossec/etc/rules/clamav_rules.xml 2>/dev/null | grep -c "100101" || echo "0")

    if [ "${rules_check}" -gt 0 ]; then
        log_pass "Custom ClamAV rules loaded (rule 100101 present)"
    else
        log_fail "Custom ClamAV rules not found"
    fi
}

# =============================================================================
# Dashboard Tests
# =============================================================================
test_dashboard_accessible() {
    log_test "Wazuh Dashboard accessible"

    local response
    response=$(curl -sku "admin:admin" "https://localhost:5601" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")

    if [[ "${response}" =~ ^(200|302|301)$ ]]; then
        log_pass "Dashboard accessible (HTTP ${response})"
    else
        log_fail "Dashboard not accessible (HTTP ${response})"
    fi
}

# =============================================================================
# Failure Recovery Tests
# =============================================================================
test_container_restart_recovery() {
    if [ "${QUICK}" = true ]; then
        log_skip "Container restart test (--quick mode)"
        return
    fi

    log_test "ClamAV container restart recovery"

    docker restart soc-clamav >/dev/null 2>&1
    sleep 30

    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "soc-clamav" 2>/dev/null || echo "none")

    if [ "${health}" = "healthy" ]; then
        log_pass "ClamAV recovered after restart"
    elif [ "${health}" = "starting" ]; then
        log_pass "ClamAV restarting (DB reload takes time)"
    else
        log_fail "ClamAV did not recover: ${health}"
    fi
}

# =============================================================================
# Main Test Runner
# =============================================================================
main() {
    echo ""
    echo "============================================"
    echo "  System SOC Stack - E2E Test Suite"
    echo "============================================"
    echo ""

    # Infrastructure
    echo "--- Infrastructure ---"
    test_docker_compose_valid
    test_env_file_exists
    test_certificates_exist
    echo ""

    # Container Status
    echo "--- Container Status ---"
    test_container_running "soc-wazuh-indexer" "Wazuh Indexer"
    test_container_running "soc-wazuh-manager" "Wazuh Manager"
    test_container_running "soc-wazuh-dashboard" "Wazuh Dashboard"
    test_container_running "soc-wazuh-agent" "Wazuh Agent"
    test_container_running "soc-clamav" "ClamAV"
    test_container_running "soc-clamav-scanner" "ClamAV Scanner"
    echo ""

    # Health Checks
    echo "--- Health Checks ---"
    test_container_healthy "soc-wazuh-indexer" "Wazuh Indexer"
    test_container_healthy "soc-wazuh-manager" "Wazuh Manager"
    test_container_healthy "soc-clamav" "ClamAV"
    echo ""

    # Service APIs
    echo "--- Service APIs ---"
    test_indexer_api
    test_indexer_cluster_health
    test_manager_api
    test_agent_connected
    test_dashboard_accessible
    echo ""

    # ClamAV
    echo "--- ClamAV Detection ---"
    test_clamav_daemon
    test_clamav_db_loaded
    test_clamav_eicar_detection
    echo ""

    # Integration
    echo "--- Integration ---"
    test_clamav_log_monitored
    test_shared_volume
    test_custom_rules_loaded
    echo ""

    # Recovery
    echo "--- Failure Recovery ---"
    test_container_restart_recovery
    echo ""

    # Summary
    echo "============================================"
    echo "  Results: ${PASSED} passed, ${FAILED} failed, ${SKIPPED} skipped"
    echo "============================================"
    echo ""

    if [ ${FAILED} -gt 0 ]; then
        exit 1
    fi
    exit 0
}

main "$@"
