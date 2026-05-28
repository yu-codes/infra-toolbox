#!/bin/bash
# =============================================================================
# System SOC Stack - Certificate Generation Script
# =============================================================================
# Generates all required SSL/TLS certificates for the SOC stack.
# Can be run standalone or called by setup.sh.
#
# Usage: ./scripts/generate-certs.sh [--force]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
CERT_DIR="${PROJECT_DIR}/certs"
DAYS=3650

FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

if [ -f "${CERT_DIR}/root-ca.pem" ] && [ "${FORCE}" = false ]; then
    echo "[INFO] Certificates already exist. Use --force to regenerate."
    exit 0
fi

echo "[INFO] Generating certificates in ${CERT_DIR}/"
mkdir -p "${CERT_DIR}"

# Use relative paths from cert directory (fixes OpenSSL on MINGW/Windows)
pushd "${CERT_DIR}" > /dev/null

# Root CA
echo "[INFO] Generating Root CA..."
openssl genrsa -out root-ca-key.pem 4096
openssl req -new -x509 -sha256 \
    -key root-ca-key.pem \
    -subj "/C=TW/O=Infra/OU=SOC/CN=SOC-Root-CA" \
    -out root-ca.pem \
    -days ${DAYS}

# Admin certificate
echo "[INFO] Generating Admin certificate..."
openssl genrsa -out admin-key.pem 4096
openssl req -new \
    -key admin-key.pem \
    -subj "/C=TW/O=Infra/OU=SOC/CN=admin" \
    -out admin.csr
openssl x509 -req -sha256 \
    -in admin.csr \
    -CA root-ca.pem \
    -CAkey root-ca-key.pem \
    -CAcreateserial \
    -out admin.pem \
    -days ${DAYS}

# Function to generate service certificate with SAN
generate_cert() {
    local name=$1
    local cn=$2
    shift 2
    local sans=("$@")

    echo "[INFO] Generating ${name} certificate (CN=${cn})..."

    openssl genrsa -out "${name}-key.pem" 4096

    # Build SAN extension config
    cat > "${name}-san.cnf" <<SANEOF
[req]
distinguished_name = req_dn
req_extensions = v3_req
prompt = no

[req_dn]
C = TW
O = Infra
OU = SOC
CN = ${cn}

[v3_req]
subjectAltName = @alt_names

[alt_names]
SANEOF

    local idx=1
    for san in "${sans[@]}"; do
        echo "DNS.${idx} = ${san}" >> "${name}-san.cnf"
        idx=$((idx + 1))
    done
    echo "IP.1 = 127.0.0.1" >> "${name}-san.cnf"

    openssl req -new \
        -key "${name}-key.pem" \
        -config "${name}-san.cnf" \
        -out "${name}.csr"

    openssl x509 -req -sha256 \
        -in "${name}.csr" \
        -CA root-ca.pem \
        -CAkey root-ca-key.pem \
        -CAcreateserial \
        -out "${name}.pem" \
        -days ${DAYS} \
        -extfile "${name}-san.cnf" \
        -extensions v3_req

    rm -f "${name}-san.cnf"
}

# Generate service certificates
generate_cert "indexer" "wazuh-indexer" "wazuh-indexer" "localhost" "soc-wazuh-indexer"
generate_cert "manager" "wazuh-manager" "wazuh-manager" "localhost" "soc-wazuh-manager"
generate_cert "dashboard" "wazuh-dashboard" "wazuh-dashboard" "localhost" "soc-wazuh-dashboard"

# Cleanup
rm -f *.csr *.srl

# Set permissions
chmod 600 *-key.pem
chmod 644 *.pem

popd > /dev/null

echo "[OK] All certificates generated successfully."
echo ""
echo "Files:"
ls -la "${CERT_DIR}"/*.pem
