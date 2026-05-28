#!/bin/bash
# =============================================================================
# System SOC Stack - Health Check Script
# =============================================================================
# Checks all SOC stack services and reports status.
# Exit codes: 0 = all healthy, 1 = degraded, 2 = critical
#
# Usage: ./scripts/health-check.sh [--json] [--verbose]
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# Flags
JSON_OUTPUT=false
VERBOSE=false

for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --verbose|-v) VERBOSE=true ;;
    esac
done

# Colors (disabled for JSON mode)
if [ "${JSON_OUTPUT}" = false ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' NC=''
fi

# Counters
HEALTHY=0
UNHEALTHY=0
WARNINGS=0
RESULTS=()

check_container() {
    local name=$1
    local container="soc-${name}"

    local running
    running=$(docker inspect --format='{{.State.Running}}' "${container}" 2>/dev/null || echo "false")

    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "none")

    local uptime
    uptime=$(docker inspect --format='{{.State.StartedAt}}' "${container}" 2>/dev/null || echo "unknown")

    local status="unknown"
    if [ "${running}" = "true" ]; then
        if [ "${health}" = "healthy" ]; then
            status="healthy"
            HEALTHY=$((HEALTHY + 1))
        elif [ "${health}" = "starting" ]; then
            status="starting"
            WARNINGS=$((WARNINGS + 1))
        else
            status="unhealthy"
            UNHEALTHY=$((UNHEALTHY + 1))
        fi
    else
        status="stopped"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi

    RESULTS+=("{\"name\":\"${container}\",\"status\":\"${status}\",\"running\":${running},\"health\":\"${health}\",\"started\":\"${uptime}\"}")

    if [ "${JSON_OUTPUT}" = false ]; then
        case ${status} in
            healthy)  echo -e "  ${GREEN}✓${NC} ${container}: ${status}" ;;
            starting) echo -e "  ${YELLOW}◌${NC} ${container}: ${status}" ;;
            *)        echo -e "  ${RED}✗${NC} ${container}: ${status}" ;;
        esac
    fi
}

check_disk_usage() {
    local volumes_path="/var/lib/docker/volumes"
    local usage
    usage=$(df "${volumes_path}" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%' || echo "0")

    if [ "${usage}" -gt 90 ]; then
        UNHEALTHY=$((UNHEALTHY + 1))
        if [ "${JSON_OUTPUT}" = false ]; then
            echo -e "  ${RED}✗${NC} Disk usage: ${usage}% (CRITICAL)"
        fi
    elif [ "${usage}" -gt 75 ]; then
        WARNINGS=$((WARNINGS + 1))
        if [ "${JSON_OUTPUT}" = false ]; then
            echo -e "  ${YELLOW}◌${NC} Disk usage: ${usage}% (WARNING)"
        fi
    else
        HEALTHY=$((HEALTHY + 1))
        if [ "${JSON_OUTPUT}" = false ]; then
            echo -e "  ${GREEN}✓${NC} Disk usage: ${usage}%"
        fi
    fi
}

check_indexer_api() {
    local password
    password=$(grep INDEXER_PASSWORD "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "")

    if [ -n "${password}" ]; then
        local response
        response=$(curl -sku "admin:${password}" "https://localhost:9200/_cluster/health" 2>/dev/null || echo "")

        if echo "${response}" | grep -q '"status":"green"'; then
            HEALTHY=$((HEALTHY + 1))
            [ "${JSON_OUTPUT}" = false ] && echo -e "  ${GREEN}✓${NC} Indexer cluster: green"
        elif echo "${response}" | grep -q '"status":"yellow"'; then
            WARNINGS=$((WARNINGS + 1))
            [ "${JSON_OUTPUT}" = false ] && echo -e "  ${YELLOW}◌${NC} Indexer cluster: yellow"
        else
            UNHEALTHY=$((UNHEALTHY + 1))
            [ "${JSON_OUTPUT}" = false ] && echo -e "  ${RED}✗${NC} Indexer cluster: unavailable"
        fi
    fi
}

check_clamav_db() {
    local db_age
    db_age=$(docker exec soc-clamav find /var/lib/clamav -name "*.cvd" -mtime +3 2>/dev/null | wc -l || echo "0")

    if [ "${db_age}" -gt 0 ]; then
        WARNINGS=$((WARNINGS + 1))
        [ "${JSON_OUTPUT}" = false ] && echo -e "  ${YELLOW}◌${NC} ClamAV DB: outdated (>3 days)"
    else
        HEALTHY=$((HEALTHY + 1))
        [ "${JSON_OUTPUT}" = false ] && echo -e "  ${GREEN}✓${NC} ClamAV DB: up to date"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    if [ "${JSON_OUTPUT}" = false ]; then
        echo ""
        echo "=== System SOC Stack Health Check ==="
        echo ""
        echo "Containers:"
    fi

    # Check all containers
    check_container "wazuh-indexer"
    check_container "wazuh-manager"
    check_container "wazuh-dashboard"
    check_container "wazuh-agent"
    check_container "clamav"
    check_container "clamav-scanner"

    if [ "${JSON_OUTPUT}" = false ]; then
        echo ""
        echo "Services:"
    fi

    # Service-level checks
    check_indexer_api
    check_clamav_db
    check_disk_usage

    # Summary
    local overall="healthy"
    local exit_code=0

    if [ ${UNHEALTHY} -gt 0 ]; then
        overall="critical"
        exit_code=2
    elif [ ${WARNINGS} -gt 0 ]; then
        overall="degraded"
        exit_code=1
    fi

    if [ "${JSON_OUTPUT}" = true ]; then
        local results_json
        results_json=$(printf '%s,' "${RESULTS[@]}" | sed 's/,$//')
        echo "{\"status\":\"${overall}\",\"healthy\":${HEALTHY},\"unhealthy\":${UNHEALTHY},\"warnings\":${WARNINGS},\"services\":[${results_json}]}"
    else
        echo ""
        echo "--- Summary ---"
        echo -e "Overall: ${overall} (healthy:${HEALTHY} warnings:${WARNINGS} unhealthy:${UNHEALTHY})"
        echo ""
    fi

    exit ${exit_code}
}

main "$@"
