#!/bin/bash
# =============================================================================
# System SOC Stack - EICAR Test Script
# =============================================================================
# Tests ClamAV detection capability using the EICAR test file.
# The EICAR test file is a standard antivirus test pattern that all AV
# products should detect. It is NOT a real virus.
#
# Usage: ./scripts/test-eicar.sh
# =============================================================================

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "[INFO] $1"; }
log_ok()    { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail()  { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
TEST_DIR="/tmp/soc-test-$$"
ERRORS=0

cleanup() {
    rm -rf "${TEST_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "${TEST_DIR}"

echo ""
echo "=== EICAR Antivirus Detection Test ==="
echo ""

# =============================================================================
# Test 1: Create EICAR test file
# =============================================================================
log_info "Test 1: Creating EICAR test file..."

# EICAR standard test string (this is NOT a virus)
EICAR_STRING='X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

echo "${EICAR_STRING}" > "${TEST_DIR}/eicar.txt"

if [ -f "${TEST_DIR}/eicar.txt" ]; then
    log_ok "EICAR test file created: ${TEST_DIR}/eicar.txt"
else
    log_fail "Failed to create EICAR test file"
    ERRORS=$((ERRORS + 1))
fi

# =============================================================================
# Test 2: ClamAV detection via clamdscan (daemon)
# =============================================================================
log_info "Test 2: Testing ClamAV daemon detection..."

# Copy test file to a location ClamAV container can access
docker cp "${TEST_DIR}/eicar.txt" soc-clamav:/tmp/eicar-test.txt 2>/dev/null

SCAN_RESULT=$(docker exec soc-clamav clamdscan /tmp/eicar-test.txt 2>&1 || true)

if echo "${SCAN_RESULT}" | grep -q "FOUND"; then
    log_ok "ClamAV daemon detected EICAR test file"
    echo "       Result: $(echo "${SCAN_RESULT}" | grep "FOUND")"
else
    log_fail "ClamAV daemon did NOT detect EICAR test file"
    echo "       Output: ${SCAN_RESULT}"
    ERRORS=$((ERRORS + 1))
fi

# Cleanup test file in container
docker exec soc-clamav rm -f /tmp/eicar-test.txt 2>/dev/null

# =============================================================================
# Test 3: ClamAV detection via scan script
# =============================================================================
log_info "Test 3: Testing scan script detection..."

# Create test file in scannable location
docker exec soc-clamav sh -c "echo '${EICAR_STRING}' > /tmp/eicar-scan-test.txt" 2>/dev/null

# Run scan script in scanner container
docker exec soc-clamav-scanner sh -c "
    export CLAMAV_SCAN_PATHS=/tmp
    /scripts/clamav-scan.sh
" 2>/dev/null || true

# Check scan log for detection
sleep 2
SCAN_LOG=$(docker exec soc-clamav-scanner cat /var/log/clamav/scan.log 2>/dev/null | tail -5)

if echo "${SCAN_LOG}" | grep -q "MALWARE_DETECTED\|FOUND"; then
    log_ok "Scan script detected EICAR and logged correctly"
    echo "       Log entry: $(echo "${SCAN_LOG}" | grep "MALWARE_DETECTED\|FOUND" | tail -1)"
else
    log_warn "Scan script detection not verified in log (may need more time)"
    echo "       Recent log: ${SCAN_LOG}"
fi

# Cleanup
docker exec soc-clamav rm -f /tmp/eicar-scan-test.txt 2>/dev/null

# =============================================================================
# Test 4: Verify Wazuh receives alert
# =============================================================================
log_info "Test 4: Checking Wazuh alert generation..."
log_info "  (Waiting 30 seconds for log ingestion...)"
sleep 30

# Check Wazuh alerts
WAZUH_ALERTS=$(docker exec soc-wazuh-manager cat /var/ossec/logs/alerts/alerts.json 2>/dev/null | \
    grep -i "eicar\|clamav\|malware" | tail -3)

if [ -n "${WAZUH_ALERTS}" ]; then
    log_ok "Wazuh generated alert for ClamAV detection"
    echo "       Alert: $(echo "${WAZUH_ALERTS}" | tail -1 | head -c 200)"
else
    log_warn "No Wazuh alert found yet (may need more time for processing)"
    echo "       Check dashboard manually or wait and re-run"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=== Test Summary ==="
if [ ${ERRORS} -eq 0 ]; then
    log_ok "All critical tests passed"
    echo ""
    echo "Next steps:"
    echo "  1. Open Wazuh Dashboard: https://localhost:5601"
    echo "  2. Go to Security Events"
    echo "  3. Search for 'clamav' or 'EICAR'"
    echo "  4. Verify alert level 7+ is shown"
else
    log_fail "${ERRORS} test(s) failed"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check ClamAV status: docker exec soc-clamav clamdscan --version"
    echo "  - Check scan log: docker exec soc-clamav cat /var/log/clamav/scan.log"
    echo "  - Check Wazuh agent: docker exec soc-wazuh-agent /var/ossec/bin/wazuh-control status"
fi
echo ""

exit ${ERRORS}
