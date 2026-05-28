#!/bin/sh
# =============================================================================
# ClamAV Scheduled Scan Script
# =============================================================================
# This script performs scheduled antivirus scans and outputs results in a format
# that Wazuh can ingest via localfile monitoring.
#
# Log format: timestamp|scan_type|path|status|details
# =============================================================================

set -e

# Configuration
SCAN_PATHS="${CLAMAV_SCAN_PATHS:-/scandir}"
LOG_DIR="/var/log/clamav"
SCAN_LOG="${LOG_DIR}/scan.log"
SCAN_SUMMARY="${LOG_DIR}/scan_summary.log"
MAX_FILE_SIZE="${CLAMAV_MAX_FILE_SIZE:-100M}"
EXCLUDE_DIRS="/scandir/proc /scandir/sys /scandir/dev /scandir/run /scandir/var/lib/clamav"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Build exclude arguments
EXCLUDE_ARGS=""
for dir in ${EXCLUDE_DIRS}; do
    EXCLUDE_ARGS="${EXCLUDE_ARGS} --exclude-dir=${dir}"
done

echo "[${TIMESTAMP}] ClamAV scan started - paths: ${SCAN_PATHS}" >> "${SCAN_LOG}"

# Run clamscan with structured output
# Using clamscan (standalone) instead of clamdscan for scheduled full scans
clamscan \
    --recursive \
    --infected \
    --no-summary \
    --max-filesize="${MAX_FILE_SIZE}" \
    --max-scansize=400M \
    --max-recursion=16 \
    --max-dir-recursion=20 \
    ${EXCLUDE_ARGS} \
    "${SCAN_PATHS}" 2>/dev/null | while IFS= read -r line; do
        # Format: /path/to/file: Virus.Name FOUND
        if echo "${line}" | grep -q "FOUND$"; then
            FILE_PATH=$(echo "${line}" | sed 's/: .* FOUND$//')
            VIRUS_NAME=$(echo "${line}" | sed 's/^.*: //' | sed 's/ FOUND$//')
            echo "${TIMESTAMP} clamav: MALWARE_DETECTED - file:${FILE_PATH} signature:${VIRUS_NAME} action:QUARANTINE status:FOUND" >> "${SCAN_LOG}"
        elif echo "${line}" | grep -q "ERROR$"; then
            FILE_PATH=$(echo "${line}" | sed 's/: .* ERROR$//')
            echo "${TIMESTAMP} clamav: SCAN_ERROR - file:${FILE_PATH} status:ERROR" >> "${SCAN_LOG}"
        fi
    done

# Capture exit code
SCAN_EXIT=$?

# Write summary
END_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
case ${SCAN_EXIT} in
    0)
        echo "${END_TIMESTAMP} clamav: SCAN_COMPLETED - result:CLEAN paths:${SCAN_PATHS} duration:$(date -d "${TIMESTAMP}" +%s 2>/dev/null || echo 'N/A')" >> "${SCAN_LOG}"
        ;;
    1)
        echo "${END_TIMESTAMP} clamav: SCAN_COMPLETED - result:INFECTED paths:${SCAN_PATHS}" >> "${SCAN_LOG}"
        ;;
    *)
        echo "${END_TIMESTAMP} clamav: SCAN_COMPLETED - result:ERROR exit_code:${SCAN_EXIT} paths:${SCAN_PATHS}" >> "${SCAN_LOG}"
        ;;
esac

echo "[${END_TIMESTAMP}] ClamAV scan finished with exit code: ${SCAN_EXIT}" >> "${SCAN_SUMMARY}"

exit 0
