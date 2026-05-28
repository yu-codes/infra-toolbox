#!/bin/bash
# =============================================================================
# System SOC Stack - Unit Tests (no Docker required)
# =============================================================================
# Validates configuration files and scripts without running containers.
#
# Usage: ./tests/test-unit.sh
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASSED=0
FAILED=0

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASSED=$((PASSED + 1)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILED=$((FAILED + 1)); }

# =============================================================================
# File Existence Tests
# =============================================================================
test_file_exists() {
    local file=$1
    local desc=$2
    if [ -f "${PROJECT_DIR}/${file}" ]; then
        log_pass "${desc}"
    else
        log_fail "${desc} (${file} missing)"
    fi
}

test_dir_exists() {
    local dir=$1
    local desc=$2
    if [ -d "${PROJECT_DIR}/${dir}" ]; then
        log_pass "${desc}"
    else
        log_fail "${desc} (${dir} missing)"
    fi
}

# =============================================================================
# Configuration Validation Tests
# =============================================================================
test_xml_valid() {
    local file=$1
    local desc=$2

    if command -v xmllint &>/dev/null; then
        if xmllint --noout "${PROJECT_DIR}/${file}" 2>/dev/null; then
            log_pass "${desc}"
        else
            log_fail "${desc} (invalid XML)"
        fi
    else
        # Basic check: matching tags
        local open_tags
        open_tags=$(grep -c '<[a-z]' "${PROJECT_DIR}/${file}" 2>/dev/null || echo "0")
        if [ "${open_tags}" -gt 0 ]; then
            log_pass "${desc} (basic check - install xmllint for full validation)"
        else
            log_fail "${desc} (empty or not XML)"
        fi
    fi
}

test_yaml_valid() {
    local file=$1
    local desc=$2

    if command -v python3 &>/dev/null && python3 -c "import yaml" 2>/dev/null; then
        if python3 -c "
import yaml, os, sys
filepath = os.path.join(os.environ.get('PROJECT_DIR',''), '${file}')
if not os.path.exists(filepath):
    filepath = '${PROJECT_DIR}/${file}'
yaml.safe_load(open(filepath))
" 2>/dev/null; then
            log_pass "${desc}"
        else
            log_fail "${desc} (invalid YAML)"
        fi
    else
        # Basic check
        if [ -s "${PROJECT_DIR}/${file}" ]; then
            log_pass "${desc} (basic check - install python3+PyYAML for full validation)"
        else
            log_fail "${desc} (empty file)"
        fi
    fi
}

test_shell_syntax() {
    local file=$1
    local desc=$2

    if bash -n "${PROJECT_DIR}/${file}" 2>/dev/null; then
        log_pass "${desc}"
    else
        log_fail "${desc} (syntax error)"
    fi
}

# =============================================================================
# Content Validation Tests
# =============================================================================
test_no_latest_tag() {
    local file="docker-compose.yml"
    if grep -q ":latest" "${PROJECT_DIR}/${file}" 2>/dev/null; then
        log_fail "docker-compose.yml uses :latest tag (should use specific version)"
    else
        log_pass "docker-compose.yml uses pinned image versions"
    fi
}

test_clamav_rules_have_ids() {
    local file="config/wazuh-manager/rules/clamav_rules.xml"
    local rule_count
    rule_count=$(grep -c 'rule id="100' "${PROJECT_DIR}/${file}" 2>/dev/null || echo "0")

    if [ "${rule_count}" -ge 5 ]; then
        log_pass "ClamAV rules file has ${rule_count} rules defined"
    else
        log_fail "ClamAV rules file has insufficient rules (${rule_count})"
    fi
}

test_agent_monitors_clamav() {
    local file="config/wazuh-agent/ossec.conf"
    if grep -q "/var/log/clamav/scan.log" "${PROJECT_DIR}/${file}" 2>/dev/null; then
        log_pass "Agent config monitors ClamAV scan log"
    else
        log_fail "Agent config missing ClamAV scan log monitoring"
    fi
}

test_scan_script_outputs_format() {
    local file="scripts/clamav-scan.sh"
    if grep -q "MALWARE_DETECTED" "${PROJECT_DIR}/${file}" 2>/dev/null; then
        log_pass "Scan script outputs structured MALWARE_DETECTED format"
    else
        log_fail "Scan script missing structured output format"
    fi
}

test_env_example_complete() {
    local file=".env.example"
    local required_vars=(INDEXER_PASSWORD WAZUH_MANAGER_API_PASSWORD DASHBOARD_PORT CLAMAV_SCAN_SCHEDULE)
    local missing=0

    for var in "${required_vars[@]}"; do
        if ! grep -q "${var}" "${PROJECT_DIR}/${file}" 2>/dev/null; then
            missing=$((missing + 1))
        fi
    done

    if [ ${missing} -eq 0 ]; then
        log_pass ".env.example has all required variables"
    else
        log_fail ".env.example missing ${missing} required variable(s)"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "=== SOC Stack Unit Tests ==="
    echo ""

    echo "--- File Existence ---"
    test_file_exists "docker-compose.yml" "docker-compose.yml exists"
    test_file_exists ".env.example" ".env.example exists"
    test_file_exists "README.md" "README.md exists"
    test_file_exists "config/clamav/clamd.conf" "ClamAV daemon config exists"
    test_file_exists "config/clamav/freshclam.conf" "Freshclam config exists"
    test_file_exists "config/wazuh-manager/ossec.conf" "Manager ossec.conf exists"
    test_file_exists "config/wazuh-agent/ossec.conf" "Agent ossec.conf exists"
    test_file_exists "config/wazuh-manager/rules/clamav_rules.xml" "Custom rules exist"
    test_file_exists "scripts/setup.sh" "Setup script exists"
    test_file_exists "scripts/clamav-scan.sh" "ClamAV scan script exists"
    test_file_exists "scripts/health-check.sh" "Health check script exists"
    test_file_exists "scripts/maintenance.sh" "Maintenance script exists"
    test_file_exists "scripts/log-rotation.sh" "Log rotation script exists"
    test_dir_exists "tests" "Tests directory exists"
    echo ""

    echo "--- Configuration Validation ---"
    test_xml_valid "config/wazuh-manager/ossec.conf" "Manager ossec.conf is valid XML"
    test_xml_valid "config/wazuh-agent/ossec.conf" "Agent ossec.conf is valid XML"
    test_xml_valid "config/wazuh-manager/rules/clamav_rules.xml" "ClamAV rules is valid XML"
    test_yaml_valid "config/wazuh-indexer/internal_users.yml" "Internal users is valid YAML"
    echo ""

    echo "--- Shell Script Syntax ---"
    test_shell_syntax "scripts/setup.sh" "setup.sh syntax OK"
    test_shell_syntax "scripts/clamav-scan.sh" "clamav-scan.sh syntax OK"
    test_shell_syntax "scripts/health-check.sh" "health-check.sh syntax OK"
    test_shell_syntax "scripts/maintenance.sh" "maintenance.sh syntax OK"
    test_shell_syntax "scripts/log-rotation.sh" "log-rotation.sh syntax OK"
    test_shell_syntax "scripts/generate-certs.sh" "generate-certs.sh syntax OK"
    test_shell_syntax "scripts/test-eicar.sh" "test-eicar.sh syntax OK"
    echo ""

    echo "--- Content Validation ---"
    test_no_latest_tag
    test_clamav_rules_have_ids
    test_agent_monitors_clamav
    test_scan_script_outputs_format
    test_env_example_complete
    echo ""

    echo "=== Results: ${PASSED} passed, ${FAILED} failed ==="
    echo ""

    [ ${FAILED} -gt 0 ] && exit 1
    exit 0
}

main "$@"
