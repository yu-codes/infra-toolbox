#!/usr/bin/env bash
set -euo pipefail

# 避免交互提示（例如設定檔覆蓋）
export DEBIAN_FRONTEND=noninteractive

LOG_DIR="${1:-./logs}"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/cve_check_${TIMESTAMP}.txt"
JSON_FILE="$LOG_DIR/cve_status_${TIMESTAMP}.json"
CHANGELOG_DIR="$LOG_DIR/changelogs_${TIMESTAMP}"

# 檢測是否有 Ubuntu Pro
HAS_PRO=false
if command -v pro &>/dev/null; then
  if pro status 2>/dev/null | grep -q "attached: True\|status: attached"; then
    HAS_PRO=true
  fi
fi

# 取得安全狀態 JSON 的函數
get_security_status_json() {
  if [[ "$HAS_PRO" == "true" ]]; then
    pro security-status --format json 2>/dev/null || echo '{"error": "pro security-status failed"}'
  else
    ubuntu-security-status --format json 2>/dev/null || echo '{"error": "ubuntu-security-status failed"}'
  fi
}

# 取得安全狀態文字輸出的函數
get_security_status_text() {
  if [[ "$HAS_PRO" == "true" ]]; then
    pro security-status 2>/dev/null || ubuntu-security-status 2>/dev/null || echo "無法取得安全狀態"
  else
    ubuntu-security-status 2>/dev/null || pro security-status 2>/dev/null || echo "無法取得安全狀態"
  fi
}

# 收集套件 changelog（包含 CVE/USN 資訊）
collect_changelogs() {
  local pkgs=("$@")
  if [[ ${#pkgs[@]} -eq 0 ]]; then
    echo "無需收集 changelog"
    return
  fi
  
  mkdir -p "$CHANGELOG_DIR"
  echo "收集 ${#pkgs[@]} 個套件的 changelog..."
  
  for pkg in "${pkgs[@]}"; do
    echo "  - 取得 $pkg 的 changelog..."
    apt-get changelog "$pkg" > "$CHANGELOG_DIR/${pkg}.changelog" 2>/dev/null || \
      echo "無法取得 $pkg 的 changelog" > "$CHANGELOG_DIR/${pkg}.changelog"
  done
  
  echo "Changelog 已存放於：$CHANGELOG_DIR"
}

# 取得可升級的安全套件列表
get_security_packages() {
  apt list --upgradable 2>/dev/null | grep -i security | cut -d'/' -f1 || true
}

{
  echo "===== CVE 漏洞檢查開始：$(date '+%F %T') ====="
  echo "運行模式：$(if [[ "$HAS_PRO" == "true" ]]; then echo "Ubuntu Pro（已附加）"; else echo "標準版（無 Pro）"; fi)"

  # [1] 更新套件索引
  echo -e "\n[1/7] 更新套件索引"
  sudo apt-get update -qq

  # [2] 檢查系統安全狀態（文字）
  echo -e "\n[2/7] 系統安全狀態"
  get_security_status_text

  # [3] 輸出 JSON 格式安全狀態（供後續分析）
  echo -e "\n[3/7] 匯出安全狀態 JSON"
  get_security_status_json > "$JSON_FILE"
  echo "JSON 狀態已寫入：$JSON_FILE"
  
  # 解析 JSON 摘要（如有 jq）
  if command -v jq &>/dev/null && [[ -f "$JSON_FILE" ]]; then
    echo "--- 安全狀態摘要 ---"
    jq -r '
      if .packages then
        "總套件數: \(.packages | length // 0)",
        "需要修補: \([.packages[]? | select(.status == "needs_fix")] | length)",
        "ESM 可用: \([.packages[]? | select(.esm_available == true)] | length)"
      else
        "無法解析套件資訊"
      end
    ' "$JSON_FILE" 2>/dev/null || echo "JSON 解析略過"
  fi

  # [4] 列出有安全更新的套件
  echo -e "\n[4/7] 可用的安全更新"
  UPGRADABLE=$(apt list --upgradable 2>/dev/null || true)
  if echo "$UPGRADABLE" | grep -qi security; then
    echo "$UPGRADABLE" | grep -i security
    SECURITY_PKGS=$(echo "$UPGRADABLE" | grep -i security | cut -d'/' -f1)
  else
    echo "所有可升級套件："
    echo "$UPGRADABLE"
    SECURITY_PKGS=$(echo "$UPGRADABLE" | tail -n +2 | cut -d'/' -f1)
  fi

  # [5] 收集受影響套件的 changelog（含 CVE/USN 證據）
  echo -e "\n[5/7] 收集套件 Changelog（CVE/USN 證據）"
  if [[ -n "$SECURITY_PKGS" ]]; then
    # 轉換為陣列
    mapfile -t PKG_ARRAY <<< "$SECURITY_PKGS"
    # 最多收集前 10 個套件的 changelog
    collect_changelogs "${PKG_ARRAY[@]:0:10}"
  else
    echo "無安全套件需要收集 changelog"
  fi

  # [6] 執行安全更新（穩健策略）
  echo -e "\n[6/7] 執行安全更新"
  
  if [[ "$HAS_PRO" == "true" ]]; then
    echo "--- Ubuntu Pro 路線 ---"
    # 顯示 Pro 狀態
    echo "Pro 狀態："
    pro status 2>/dev/null | head -20 || true
    
    # 檢查 ESM 是否啟用
    if pro status 2>/dev/null | grep -q "esm-infra.*enabled\|esm-apps.*enabled"; then
      echo "ESM 已啟用，將包含 ESM 安全更新"
    fi
    
    # 使用 full-upgrade 確保完整修補
    echo "執行 full-upgrade..."
    sudo apt-get full-upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
    
    # 如有特定 CVE 需修補，可使用 pro fix（範例）
    # pro fix CVE-2024-XXXX
    
  else
    echo "--- 標準版路線 ---"
    # 使用 full-upgrade 確保安全修補完整套用
    echo "執行 full-upgrade..."
    sudo apt-get full-upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
  fi

  # 清理殘留套件與快取
  echo -e "\n清理殘留套件..."
  sudo apt-get autoremove --purge -y
  sudo apt-get autoclean

  # [7] 再次檢查安全狀態
  echo -e "\n[7/7] 更新後安全狀態"
  get_security_status_text
  
  # 更新後的 JSON 狀態
  echo -e "\n更新後 JSON 狀態："
  get_security_status_json > "${JSON_FILE%.json}_after.json"
  echo "更新後 JSON 已寫入：${JSON_FILE%.json}_after.json"

  echo -e "\n===== CVE 漏洞檢查結束：$(date '+%F %T') ====="
} 2>&1 | tee -a "$LOG_FILE"

echo ""
echo "📄 檢查記錄已寫入：$LOG_FILE"
echo "📊 安全狀態 JSON：$JSON_FILE"
[[ -d "$CHANGELOG_DIR" ]] && echo "📝 Changelog 目錄：$CHANGELOG_DIR"

# 顯示使用提示
if [[ "$HAS_PRO" == "true" ]]; then
  echo ""
  echo "💡 Ubuntu Pro 提示："
  echo "   - 定向修補特定 CVE：pro fix CVE-YYYY-XXXXX"
  echo "   - 查看 ESM 套件：pro security-status --esm-infra"
  echo "   - 檢查附加狀態：pro status"
fi
